from auxiliar import file
from auxiliar import thread
from crawler.base_crawler import BaseCrawler
import time
import logging
import requests
import sys
import threading

class ExtendedCrawler(BaseCrawler):
    def __init__(self, conferences, years, num_threads, output_dir):
        super().__init__(conferences, years, num_threads, output_dir)
        self.api_key = file.api_key_in_env()
        self.semaphore = threading.Semaphore(1)

    def crawl(self):
        initial_time = time.time()
        first_year, last_year = self.years
        for conf in self.conferences:
            global data_per_year
            data_per_year = {}

            data_dir = f"./data/base_crawler_data/{conf}_basic_data"
            if file.exists_file(data_dir):
                basic_data = file.load_json(data_dir)
            else:
                sys.exit(f"Error: The basic data for the conference {conf} does not exist. Please run the base crawler first.")
            
            for year in range(first_year, last_year + 1):
                if not file.year_exists_in_file(year, data_per_year):
                    logging.info(f"(EXTENDED) - {year} data not found.")
                
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
            if str(year) not in data:
                continue
            for elem in data[str(year)]:
                paper_title = elem['Title']
                paper_doi_num = elem['DOI Number']
                paper_pub_year = elem['Year']
                paper_openalex_link = elem['OpenAlex Link']
                authors_institutions = elem['Authors and Institutions']
                referenced_works = elem['OpenAlex Referenced Works']

                s2_data = self._get_s2_paper_data(paper_title, paper_doi_num)
                paper_id, abstract, tldr, embedding, citations_s2, doi_s2 = s2_data if s2_data is not None else (None, None, None, None, None, None)

                if doi_s2 is not None and paper_openalex_link is None:
                    openalex_data = super()._get_openalex_data(f"https://api.openalex.org/works/https://doi.org/{doi_s2}")
                    paper_doi_num, authors_institutions, referenced_works = openalex_data if openalex_data is not None else (None, None, None)

                paper_data.append ({
                    'Title': paper_title,
                    'Year': paper_pub_year,
                    'DOI Number': paper_doi_num,
                    'OpenAlex Link': paper_openalex_link,
                    'S2 Paper ID': paper_id,
                    'Authors and Institutions': authors_institutions,
                    'OpenAlex Referenced Works': referenced_works,
                    'Citations S2': citations_s2,
                    'Abstract': abstract,
                    'TLDR': tldr
                    #'Embedding': embedding
                })

            self.semaphore.acquire()
            data_per_year[year] = paper_data
            self.semaphore.release()



    def _get_s2_paper_data(self, title, doi):
        """This functions uses the Semantic Scholar API to get the paper data. If the DOI is not provided, it will search for the paper using the title.

        Args:
            title (string): title of the paper to search
            doi (string): DOI of the paper to search

        Returns:
            dict: A dicctionary with the paper data (paper_id, abstract, tldr, embedding, citations)
        """    
        data_results = None
        paper_data_query_params = {'fields': 'abstract,tldr,embedding,references,externalIds'}

        # if the DOI is provided, search for the paper using the DOI
        if doi is not None:
            url = f'https://api.semanticscholar.org/graph/v1/paper/{doi}'
            response = self._make_request_func(url, paper_data_query_params, self.api_key)

            time.sleep(1)
            if response.status_code == 429 or response.status_code == 504:
                time.sleep(5)
                response = self._make_request_func(url, paper_data_query_params, self.api_key)
                
            if response.status_code == 200:
                response_data = response.json()
                data_results = self._extract_s2_data(response_data)
            else:
                logging.error(f"(EXTENDED) - {response.status_code} in request for paper {title}")

        # if the DOI is not provided, search for the paper using the title
        if doi is None:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            query_params = {
                'query': title, 
                'limit': 1
            }
            response = self._make_request_func(url, query_params, self.api_key)

            time.sleep(1)
            if response.status_code == 429 or response.status_code == 504:
                time.sleep(5)
                response = self._make_request_func(url, query_params, self.api_key)

            if response.status_code == 200:
                response_data = response.json().get('data', None)
                if response_data is None:
                    return None
                paper_id = response_data[0]['paperId']
                base_url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"

                response = self._make_request_func(base_url, paper_data_query_params, self.api_key)

                if response.status_code == 429 or response.status_code == 504:
                    time.sleep(5)
                    response = self._make_request_func(base_url, paper_data_query_params, self.api_key)

                if response.status_code == 200:
                    response_data = response.json()
                    data_results = self._extract_s2_data(response_data)
                else:
                    logging.error(f"(EXTENDED) - {response.status_code} in request for paper {title}")
            else:
                logging.error(f"(EXTENDED) - {response.status_code} in request for paper {title}")

        if data_results:
            return data_results
        else:
            return None
        
    
    def _extract_s2_data(self, response_data):
        """Function that extracts the paper data from the Semantic Scholar API response. Used in the _get_paper_s2_data_request function.

        Args:
            response_data (json): the response from the Semantic Scholar API obtained in the _get_paper_s2_data_request function.

        Returns:
            tuple: all the paper data (paper_id, abstract, tldr, embedding, citations)
        """    
        tldr = None
        embedding = None
        citations = None
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

        return paper_id, abstract, tldr, embedding, citations, ids
    


    def _make_request_func(self, url, params, api_key):
        """Function that makes a request to an API and returns the response data. Used in the _get_paper_s2_data_request function.

        Args:
            url (string): the URL of the API.
            params (dict): the parameters for the request.
            headers (dict): the headers for the request.

        Returns:
            response object: the response data.
        """
        if api_key is not None:
            response = requests.get(url, params=params, headers={'x-api-key': api_key})    
        else:
            response = requests.get(url, params=params)

        return response