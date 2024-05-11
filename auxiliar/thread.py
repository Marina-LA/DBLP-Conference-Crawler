import threading
from tqdm import tqdm

class Thread:
    def __init__(self, num_threads):
        self.num_threads = num_threads

    def run(self, target, args):
        first_year, last_year = args[1:3]
        data = args[0]

        total_years = last_year - first_year + 1
        average_chunk_size = total_years // self.num_threads
        remainder = total_years % self.num_threads
        start_year = first_year

        if self.num_threads == 1:
            target(*args)
        else:
            threads = []
            for i in range(self.num_threads):
                chunk_size = average_chunk_size
                if i < remainder:
                    chunk_size += 1
                end_year = start_year + chunk_size - 1 
                t = threading.Thread(target=target, args=(data, start_year, end_year))
                threads.append(t)
                t.start()
                start_year = end_year + 1

            for t in tqdm(threads):
                t.join()