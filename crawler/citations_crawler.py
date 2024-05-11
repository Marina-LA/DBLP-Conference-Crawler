from crawler.base_crawler import BaseCrawler
import threading
import time
import sys
from auxiliar import file
from auxiliar import thread
import requests
import logging

all_citation_data = {}
papers_data = []
all_papers_id = {}

class CitationsCrawler(BaseCrawler):
    def __init__(self, conferences, years, num_threads, output_dir):
        super().__init__(conferences, years, num_threads, output_dir)
        self.semaphore_s2 = threading.Semaphore(1)
        self.semaphore_oa = threading.Semaphore(1)


    def crawl(self):
        initial_time = time.time()
        first_year, last_year = self.years
        for conf in self.conferences:
            global papers_data
            papers_data = []
            global all_citation_data
            all_citation_data = {}

            if file.exists_file(f"./data/extended_crawler_data/{conf}_extended_data"):
                extended_data = file.load_json(f"./data/extended_crawler_data/{conf}_extended_data")
            else:
                sys.exit(f"Error: The extended data for the conference {conf} does not exist. Please run the extended crawler first.")
                
            self._get_all_paper_data(self.conferences)

            threads = thread.Thread(self.num_threads)
            threads.run(self._search_citations_data, (extended_data, first_year, last_year))

            data_size = len(papers_data)
            threads.run(self._get_citation_data, (papers_data, 0, data_size))
            
            file.save_json(f"{self.output_dir}/{conf}_extended_data", all_citation_data)

        final_time = time.time()
        minutes = (final_time - initial_time) / 60
        print(f"(CITATIONS) - Done in {minutes:.3f} minutes")



    def _search_citations_data(self, data, start_year, end_year):
        papers = {}
        for year in range(start_year, end_year + 1):

            # obtain all the papers ids from the citations
            try:
                for paper in data.get(str(year), []):
                    citations = paper.get("Citations S2", [])

                    if citations:
                        paper_ids = [citation["paperId"] for citation in citations if citation.get("paperId")]
                        papers[paper["Title"]] = paper_ids
            except KeyError:
                pass

        self._batch_request_s2(papers)


    def _batch_request_s2(self, papers):
        url_s2 = "https://api.semanticscholar.org/graph/v1/paper/batch"
        #print("Making requests to Semantic Scholar API...")
        for title, citations in papers.items():
            responses = []
            citations_len = len(citations)
            num_iterations = citations_len // 500
            rest = num_iterations + 1 if citations_len % 500 > 0 else num_iterations
            for j in range(rest):
                ini = j * 500
                fin = min((j + 1) * 500, citations_len)
                c = citations[ini:fin]
                r = requests.post(url_s2,
                    params={'fields': 'title,year,venue,externalIds,authors.name'},
                    json={"ids": c})
                time.sleep(1.25)
                if r.status_code == 200:
                    responses.append(r.json())
                else:
                    logging.error(f"(CITATIONS) - {r.status_code} in request for paper {title}")

            self.semaphore_s2.acquire()
            papers_data.append({"Title": title, "Response": responses})
            self.semaphore_s2.release()


    def _get_citation_data(self, data, start, end):
        #i = 0
        for elem in data[start:end]:
            cited_data = []
            main_paper_title = elem.get("Title", None)
            response = elem.get("Response", None)
            if response == []: continue

            for cited_paper in response:
                if type(cited_paper) is list:
                    for c in cited_paper:
                        #i += 1
                        data = self._get_cited_paper_data(c)
                        cited_data.append(data)
                else:
                    #i += 1
                    data = self._get_cited_paper_data(cited_paper)
                    cited_data.append(data)
            
            self.semaphore_oa.acquire()
            all_citation_data[main_paper_title] = cited_data
            self.semaphore_oa.release()



    def _get_cited_paper_data(self, cited_paper):
        url_openalex = "https://api.openalex.org/works/"    
        # if there is no data, continue with the next paper
        if cited_paper is None:
            return

        authors = []
        title = cited_paper.get("title", None)
        paper_id = cited_paper.get("paperId", None)
        venue = cited_paper.get("venue", None)
        link = cited_paper.get("externalIds", None).get("DOI", None)
        year = cited_paper.get("year", None)

        # check if the paper is in the already existing data
        if paper_id in all_papers_id:
            authors = all_papers_id[paper_id]["Paper"]['Authors and Institutions']
            venue = all_papers_id[paper_id]['Conference']
            year = all_papers_id[paper_id]["Paper"]['Year']
        elif link is not None:
            title_aux, authors = self._get_openalex_data(f"{url_openalex}https://doi.org/{link}")
            if title_aux == "not found":
                title = title_aux
        else:  
            auth = cited_paper["authors"]
            for a in auth:
                authors.append({"Author": a["name"], "Institutions": None})

        return {"Title": title, "Authors": authors, "Venue": venue, "Year": year}
    

    def _get_openalex_data(self, openalex_link):
        """Function that extracts the authors and institutions data and the referenced works from the OpenAlex API.

        Args:
            openalex_link (string): the link to the OpenAlex API work obtained from the initial data (dblp).

        Returns:
            tuple: authors and institutions data and the referenced works or None if there is no data.
        """    
        response = requests.get(openalex_link)
        if response.status_code == 200:
            response_data = response.json()
            title = response_data.get('title', None)
            authors_institutions = self._get_authors_and_institutions(response_data)
            return title, authors_institutions
        else:
            logging.error(f"(CITATIONS) - {response.status_code} in request for link {openalex_link}")
            return  None, None



    def _get_authors_and_institutions(self, response_data):
        """This function extracts the authors and institutions data from the OpenAlex API response. Used in the _get_openalex_data function.

        Args:
            response_data (json): the data obtained from the OpenAlex API response in the function _get_openalex_data.

        Returns:
            list: a list with all the authors and their institutions data.
        """    
        auth_data = []
        authors = response_data['authorships']
        if authors == []: return None
        for a in authors:
            institutions = []
            author_name = a['author']['display_name']
            author_institutions = a['institutions']
            for inst in author_institutions:
                institution_name = inst.get('display_name', None)
                institution_country = inst.get('country_code', None)
                institutions.append({'Institution Name': institution_name, 'Country': institution_country})
                """
                institution_data = _get_institution_data(inst)
                institutions.append(institution_data)
                """        
            auth_data.append({'Author': author_name, 'Institutions': institutions if institutions != [] else None})
        
        return auth_data

    
    def _get_all_paper_data(self, conferences):  
        for conf in conferences:
            data = file.load_json(f"./data/extended_crawler_data/{conf}_extended_data")
            for year, paper in data.items():
                for p in paper:
                    all_papers_id[p["S2 Paper ID"]] = {"Paper": p, "Conference": conf}