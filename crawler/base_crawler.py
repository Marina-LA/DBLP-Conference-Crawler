import time
import threading
from auxiliar import file, thread
from bs4 import BeautifulSoup
import requests
import re
import logging

data_per_year = {}


class BaseCrawler:
    def __init__(self, conferences, years, num_threads, output_dir):
        self.conferences = conferences
        self.years = years
        self.num_threads = num_threads
        self.output_dir = output_dir
        self.semaphore = threading.Semaphore(1)
    
    def crawl(self):
        initial_time = time.time()
        first_year, last_year = self.years
        for conf in self.conferences:
            global data_per_year
            data_per_year = {}
                
            threads = thread.Thread(self.num_threads)
            threads.run(self._search, (conf, first_year, last_year))
            
            file.save_json(f"{self.output_dir}/{conf}_basic_data", data_per_year)

        final_time = time.time()
        minutes = (final_time - initial_time) / 60
        print(f"(BASE) - Done in {minutes:.3f} minutes")


    def _search(self, conf, first_year, last_year):
        """Retrieve all initial information of a conference and save it into a JSON file.

        Args:
            conf (string): The name of the conference from which we want to search for information.
            first_year (int): The first year from which we want to search for information.
            last_year (int): The last year from which we want to search for information.
        """    

        links = self._get_links(conf)
        valid_links = []
        for link in links:
            if self._filter_dblp_links(conf, link) and any(str(year) in link for year in range(first_year, last_year + 1)):
                valid_links.append(link)

        for link in valid_links:
            pub_list_raw = self._get_pub_list(link)
            for pub in pub_list_raw:
                article_items = pub.find_all('li', {'itemtype': 'http://schema.org/ScholarlyArticle'})
                header = pub.find_previous('h2')
                if self._filter_section(header.text):
                    continue
                for child in article_items:
                    pub_data = self._get_dblp_paper_data(child)
                    if pub_data is None:
                        continue
                    if pub_data['Year'] not in data_per_year:
                        self.semaphore.acquire()
                        data_per_year[pub_data['Year']] = []
                        self.semaphore.release()
                    
                    self.semaphore.acquire()
                    data_per_year[pub_data['Year']].append(pub_data)
                    self.semaphore.release()



    def _get_links(self, conference):
        """Search for the links for each year of a specific conference

        Args:
            conference (string): name of the conference in the dblp link

        Returns:
            list: list with all the links for each year
        """    
        # obtain the links for every year
        url = "https://dblp.org/db/conf/" + conference + "/"
        html_page = requests.get(url, timeout=10)
        soup = BeautifulSoup(html_page.text, 'html.parser')
        link_list = set()
        for link_elem in soup.findAll('a'):
            link = link_elem.get('href')
            if link and url in link:  # to avoid repeated links
                link_list.add(link)
        return link_list  # list with all the papers for each year



    def _get_pub_list(self, link):
        """Search all publications available on DBLP by parsing the HTML file and searching for the class named publ-list.

        Args:
            link (string): one of the links obtained from the _get_links function

        Returns:
            bs4 object: returns a list of bs4 objects with the class publ-list
        """    
        resp = requests.get(link, timeout=10)
        soup = BeautifulSoup(resp.content, features="lxml")
        return soup.findAll("ul", attrs={"class": "publ-list"})
    


    def _get_dblp_paper_data(self, publication):
        """This function extracts all the data to then pass it to the search() function.

        Args:
            publication (bs4 object): bs4 object with the class publ-list.

        Returns:
            dict: All the paper data.
        """    
        publication_year = 'nothing'
        paper_title = 'nothing'
        authors_names =[]
        authors_institutions = None

        for content_item in publication.contents:
            class_of_content_item = content_item.attrs.get('class', [0])
            if 'data' in class_of_content_item:

                # get the paper title from dblp
                paper_title = content_item.find('span', attrs={"class": "title", "itemprop": "name"}).text
                if self._filter_paper_title(paper_title):
                    return None

                # get the publication year from dblp
                for datePublished in content_item.findAll('span', attrs={"itemprop": "datePublished"}):
                    publication_year = datePublished.text
                if publication_year == 'nothing':
                    publication_year = content_item.find('meta', attrs={"itemprop": "datePublished"}).get("content")

                # get the author's names from dblp paper
                for author in content_item.findAll('span', attrs={"itemprop": "author"}):
                    authors_names.append(author.text)

            if 'publ' in class_of_content_item:
                links = content_item.contents[0].findAll("a")
                openalex_link = [l.get("href") for l in links if "openalex" in l.get("href")]
                doi_number, authors_institutions, referenced_works = self._get_openalex_data(openalex_link[0]) if openalex_link != [] else (None, None, None)

            if authors_institutions is None:
                auth_list = []
                for author in authors_names:
                    auth_list.append({'Author': author, 'Institutions': None})

        return {'Title': paper_title,
                'Year': publication_year,
                'DOI Number': doi_number,
                'OpenAlex Link': openalex_link[0] if openalex_link != [] else None, 
                'Authors and Institutions': authors_institutions if authors_institutions is not None else auth_list,
                'OpenAlex Referenced Works': referenced_works}
    

    def _get_openalex_data(self, link):
        """Function that extracts the authors and institutions data and the referenced works from the OpenAlex API.

        Args:
            openalex_link (string): the link to the OpenAlex API work obtained from the initial data (dblp).

        Returns:
            tuple: authors and institutions data and the referenced works or None if there is no data.
        """    
        response = requests.get(link)
        if response.status_code == 200:
            response_data = response.json()
            doi_link = response_data['doi']
            doi_number = doi_link.replace("https://doi.org/", "")
            authors_institutions = self._get_authors_and_institutions(response_data)
            referenced_works = self._get_referenced_works_openalex(response_data)
            return doi_number, authors_institutions, referenced_works if referenced_works != [] else None
        else:
            logging.error(f"(BASE) - {response.status_code} in request for link {link}")
            return None



    def _get_authors_and_institutions(self, response_data):
        """This function extracts the authors and institutions data from the OpenAlex API response. Used in the _get_openalex_data function.

        Args:
            response_data (json): the data obtained from the OpenAlex API response in the function _get_openalex_data.

        Returns:
            list: a list with all the authors and their institutions data.
        """    
        auth_data = []
        authors = response_data['authorships']
        for a in authors:
            institutions = []
            author_name = a['author']['display_name']
            author_institutions = a['institutions']
            for inst in author_institutions:
                institution_data = self._get_institution_data(inst)
                institutions.append(institution_data)
            
            auth_data.append({'Author': author_name, 'Institutions': institutions})
        
        return auth_data



    def _get_institution_data(self, institution):
        """Function that extracts the institution data from the OpenAlex API response. Used in the _get_authors_and_institutions function.

        Args:
            institution (string): OpenAlex Institution ID.

        Returns:
            dict: dicctionary with the institution name and country.
        """    
        id_inst = institution['id'].replace("https://openalex.org/", "")
        url = f"https://api.openalex.org/institutions/{id_inst}"
        response = requests.get(url)
        if response.status_code == 200:
            response_data = response.json()
            institution_name = response_data.get('display_name', None)
            institution_country = response_data.get('country_code', None)
            return {'Institution Name': institution_name, 'Country': institution_country}
        else:
            logging.error(f"(BASE) - {response.status_code} in request for link {url}")
            return None



    def _get_referenced_works_openalex(self, response_data):
        """Function that extracts the referenced works from the OpenAlex API response. Used in the _get_openalex_data function.

        Args:
            response_data (json): The data from the OpenAlex API response in the function _get_openalex_data.

        Returns:
            list: list with the referenced works for one paper.
        """    
        referenced_works_list = []
        referenced_works = response_data.get('referenced_works', None)
        if referenced_works is not None:
            for c in referenced_works:
                work_id = c.replace("https://openalex.org/", "")
                referenced_works_list.append(work_id)   
        return referenced_works_list
    


    def _filter_section(self, header):
        """Filter the articles that are not relevant to the search.

        Args:
            header (string): header of the publication

        Returns:
            boolean: True if this secction was to be skipped, False otherwise
        """    
        lower_header = header.lower().replace('\n', '')
        non_relevant_sections = ["workshop", "tutorial", "keynote", "panel", "poster", "demo", "doctoral", "posters", "short papers", "demos"]
        if any(section in lower_header for section in non_relevant_sections):
            return True
        return False
    

    def _filter_paper_title(self, title):
        """Filter the title of the paper

        Args:
            title (string): title of the paper

        Returns:
            boolean:True if the paper is valid, False otherwise
        """    

        pattern = r'^(Demo:|Poster:|Welcome Message)'
        coincidence = re.match(pattern, title)

        return bool(coincidence)



    def _filter_dblp_links(self, conf, link):
        """ Filters the dblp obtained links to match only the base conference"""
        # socc is the only conference that has a different name in the link
        # remebmer to add more conferences if needed
        if conf == "cloud": conf2 = "socc"
        else: conf2 = conf
            
        pattern = rf"https://dblp.org/db/conf/{conf}/{conf2}\d{{4}}\.html"
        return bool(re.match(pattern, link))