from auxiliar import file
from auxiliar import thread
from crawler.base_crawler import BaseCrawler
import time
import logging
import requests
import sys
import threading
from fuzzywuzzy import fuzz
import unicodedata

class ExtendedCrawler(BaseCrawler):
    def __init__(self, conferences, years, num_threads, output_dir):
        super().__init__(conferences, years, num_threads, output_dir)
        self.api_key = file.api_key_in_env()
        self.semaphore = threading.Semaphore(1)

    def crawl(self):
        initial_time = time.time()
        first_year, last_year = self.years
        for conf in self.conferences:
            print(f"(EXTENDED) - Crawling {conf} extended data from {first_year} to {last_year}...")
            global data_per_year
            data_per_year = {}

            data_dir = f"./data/base_crawler_data/{conf}_basic_data"
            if file.exists_file(data_dir):
                basic_data = file.load_json(data_dir)
            else:
                sys.exit(f"Error: The basic data for the conference {conf} does not exist. Please run the base crawler first.")
            
            """
            for year in range(first_year, last_year + 1):
                if not file.year_exists_in_file(year, data_per_year):
                    logging.info(f"(EXTENDED) - {year} data not found.")
            """
                
            threads = thread.Thread(self.num_threads)
            threads.run(self._get_paper_data, (basic_data, first_year, last_year))
            
            file.save_json(f"{self.output_dir}/{conf}_extended_data", data_per_year)

        final_time = time.time()
        minutes = (final_time - initial_time) / 60
        print(f"(EXTENDED) - Done in {minutes:.3f} minutes")


    def _get_paper_data(self, data, start_year, end_year):
        """Function that gets the paper data for a range of years. It uses the _get_paper_s2_data_request and _get_openalex_data functions to get the data.

        Args:
            data (dict): the data obtained with the initial search in the dblp API.
            start_year (int): first year to search
            end_year (int): last year to search
        """    

        for year in range(start_year, end_year + 1):
            paper_data = []
            openalex_data = None
            if str(year) not in data:
                continue
            for elem in data[str(year)]:
                paper_title = elem['Title']
                paper_doi_num = elem['DOI Number']
                paper_pub_year = elem['Year']
                paper_openalex_link = elem['OpenAlex Link']
                authors_institutions = elem['Authors and Institutions']
                referenced_works = elem['OpenAlex Referenced Works']

                #print(f"(EXTENDED) - Getting data for {paper_title} ({year})")
                
                s2_data = self._get_s2_paper_data(paper_title, paper_doi_num, authors_institutions, paper_title)

                if (s2_data is not None and paper_openalex_link is None) and s2_data['DOI'] is not None:
                    doi_s2 = s2_data['DOI']
                    openalex_data = super()._get_openalex_data(f"https://api.openalex.org/works/https://doi.org/{doi_s2}")
                    paper_doi_num, authors_institutions, referenced_works = openalex_data if openalex_data is not None else (None, None, None)
                    if paper_doi_num is None:
                        paper_doi_num = doi_s2

                paper_data.append ({
                    'Title': paper_title,
                    'Year': paper_pub_year,
                    'DOI Number': paper_doi_num,
                    'OpenAlex Link': paper_openalex_link,
                    'S2 Paper ID': s2_data['Paper ID'] if s2_data is not None else None,
                    'Authors and Institutions': authors_institutions,
                    'OpenAlex Referenced Works': referenced_works,
                    'Citations S2': s2_data['Citations'] if s2_data is not None else None,
                    'Abstract': s2_data['Abstract'] if s2_data is not None else None,
                    'TLDR': s2_data['TLDR'] if s2_data is not None else None,
                    #'Embedding': s2_data['Embedding'] if s2_data is not None else None,
                })

            self.semaphore.acquire()
            data_per_year[year] = paper_data
            self.semaphore.release()


    def _get_s2_paper_data(self, title, doi, authors_institutions, paper_title):
        """This functions uses the Semantic Scholar API to get the paper data. If the DOI is not provided, it will search for the paper using the title.

        Args:
            title (string): title of the paper to search
            doi (string): DOI of the paper to search

        Returns:
            dict: A dicctionary with the paper data (paper_id, abstract, tldr, embedding, citations)
        """ 
        response = None
        paper_data_query_params = {'fields': 'title,authors.name,abstract,tldr,embedding,references,externalIds'}

        # if the DOI is provided, search for the paper using the DOI
        if doi:
            response = self._get_paper_data_by_doi(doi, paper_data_query_params)
            if response is not None:
                return response
        # if the DOI is not provided, search for the paper using the title
        response_data = self._get_paper_data_by_title(title)
        if self._verify_paper(response_data, authors_institutions, paper_title):
            return response_data
        return None




    def _get_paper_data_by_doi(self, doi, params):
        url = f'https://api.semanticscholar.org/graph/v1/paper/{doi}'
        response = self._make_request_with_retries(url, params)

        if response is None:
            logging.error(f"(EXTENDED) - Paper with DOI {doi} not found in Semantic Scholar")
            return None
            
        if response.status_code == 200:
            json_response = response.json()
            return self._extract_s2_data(json_response)
        else:
            logging.error(f"(EXTENDED) - {response.status_code} in request for paper with DOI {doi}")
            return None
        


    def _get_paper_data_by_title(self, title):
        url = f"https://api.semanticscholar.org/graph/v1/paper/search/match?"
        query_params = {'query': f'{title}.', 'fields': 'title,externalIds,abstract,tldr,references,year,authors.name'}
        search_response = self._make_request_with_retries(url, query_params)

        if search_response is None:
            logging.error(f"(EXTENDED) - Paper [{title}] not found in Semantic Scholar")
            return None

        if search_response.status_code == 200:
            response_json = search_response.json().get('data', None)[0]
            if response_json:
                return self._extract_s2_data(response_json)
            else:
                logging.error(f"(EXTENDED) - Paper [{title}] not found in Semantic Scholar")
        else:
            logging.error(f"(EXTENDED) - {search_response.status_code} in request for paper [{title}]: Searching for paper by title")
        return None

        
    
    def _extract_s2_data(self, response_data):
        """Function that extracts the paper data from the Semantic Scholar API response. Used in the _get_paper_s2_data_request function.

        Args:
            response_data (json): the response from the Semantic Scholar API obtained in the _get_paper_s2_data_request function.

        Returns:
            tuple: all the paper data (paper_id, abstract, tldr, embedding, citations)
        """    
        title = response_data.get('title', None)
        paper_id = response_data.get('paperId', None)
        abstract = response_data.get('abstract', None)
        tldr = response_data.get('tldr', None)
        ids = response_data.get("externalIds", None).get("DOI", None)
        if tldr is not None:
            tldr = tldr.get('text', None)
        embedding = response_data.get('embedding', None)
        if embedding is not None:
            embedding = embedding.get('vector', None)
        citations = response_data.get('references', None)
        authors = response_data.get('authors', None)
        year = response_data.get('year', None)

        return {'Title': title, 
                'Paper ID': paper_id, 
                'Abstract': abstract, 
                'TLDR': tldr, 
                'Embedding': embedding, 
                'Citations': citations, 
                'DOI': ids, 
                'Year': year, 
                'Authors': authors   
            }
    


    def _make_request_with_retries(self, url, params, retries=2, initial_sleep=2, backoff_factor=5):
        """Function that makes a request to an API and returns the response data. Used in the _get_paper_s2_data_request function.

        Args:
            url (string): the URL of the API.
            params (dict): the parameters for the request.
            retries (int, optional): number of retries. Defaults to 2.
            initial_sleep (int, optional): initial sleep time. Defaults to 1.
            backoff_factor (int, optional): backoff factor. Defaults to 5.

        Returns:
            response object: the response data.
        """

        for attempt in range(retries+1):
            # if an API key is provided, use it in the request
            if self.api_key is not None:
                response = requests.get(url, params=params, headers={'x-api-key': self.api_key})    
            else:
                response = requests.get(url, params=params)

            # if the response is successful, return it
            if response.status_code == 200:
                return response
            # if the response is 429 or 504, sleep and try
            elif response.status_code == 429 or response.status_code == 504:
                time.sleep(initial_sleep + attempt * backoff_factor)
            else: # if the response is not successful, return None
                break
        return response if response.status_code == 200 else None
    


    def _verify_paper(self, paper_data, dblp_authors, paper_title):
        if paper_data is not None:
            #s2_year = paper_data['Year']
            s2_num_authors = len(paper_data['Authors'])
            dblp_num_authors = len(dblp_authors)
            s2_authors_names = [author['name'] for author in paper_data['Authors']]
            dblp_authors_names = [author['Author'] for author in dblp_authors]
            s2_paper_title = paper_data['Title']

            if paper_title[-1] == '.' and s2_paper_title[-1] != '.':
                s2_paper_title = f"{paper_data['Title']}."
            elif paper_title[-1] != '.' and s2_paper_title[-1] == '.': 
                s2_paper_title = paper_data['Title'][:-1]

            if paper_title.lower() == s2_paper_title.lower():
                return True
            if s2_num_authors == dblp_num_authors and self._compare_authors(dblp_authors_names, s2_authors_names):
                return True
        return False
    


    def _normalize_string(self, name):
        name = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
        )
        return name.lower().strip()
    


    def _compare_authors(self, dblp_authors, s2_authors):
        similar_authors = 0
        for i in range(len(dblp_authors)):
            similarity = fuzz.ratio(self._normalize_string(dblp_authors[i]), self._normalize_string(s2_authors[i]))
            if similarity >= 75:
                similar_authors += 1
        return similar_authors >= (len(dblp_authors) / 2)
        