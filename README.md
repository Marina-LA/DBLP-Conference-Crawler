<br/>
<div align="center">
    <img src="logo.png" alt="Logo" width="500">
</div>
<br/>
<br>
<br>
<br>

<div align="center"><strong> ⚠️ This crawler obtains the data using <a href="https://dblp.org">DBLP</a>, <a href="https://openalex.org">OpenAlex</a> and <a href="https://www.semanticscholar.org">Semantic Scholar</a> ⚠️</strong></div>

<br>
<br>

# :point_right: CRAWLER

This crawler is composed of three different crawlers, each of which extracts different data that complements each other.

- ``Base Crawler:`` Extracts the main data from papers published in a conference. This data is extracted using DBLP and OpenAlex.
- ``Extended Crawler:`` Extracts data related to cited papers and abstracts among others. The data is extracted from Semantic Scholar (and OpenAlex in certain specific cases).
- ``Citations Crawler:`` Given the citations extracted with the extended crawler, it extracts information related to the cited papers.

# :inbox_tray: Required Libraries

You can install the required libraries for the project using the following command.

```console
pip install -r requirements.txt
```

# :running: How to execute the crawler?

To run the crawler is as easy as executing the following command:

```console
python ./use_crawler.py --c {conference} --y {[from to] / year} [--extended] [--citations] [--t int] [--no_key]
```

Here's some examples:

```console
python ./use_crawler.py --c middleware cloud --y 2015 2020 --t 2 --extended 
```

Fetch the data for the middleware and SoCC conferences from 2015 to 2020. Use the **extended crawler** with two threads.

```console
python ./use_crawler.py --c nsdi --y 2023 
```

Get the data for USENIX NSDI from the year 2023. It will use the **base crawler** and a single thread.

# :key: Semantic Scholar API Key

In order to achieve a higher rate limit with Semantic Scholar, it is necessary to use an API Key. Semantic Scholar provides them for free upon filling out this [form](https://www.semanticscholar.org/product/api#api-key-form).

You can also use the crawler without an API key, but it should be noted that the request limits are quite low, so they may cause issues.

**:mag_right: To use the API Key, simply create a ``.env`` file and place it there. The crawler will automatically read it.**

## :large_blue_diamond: Arguments

- ``--c``   The name or names of the conferences from which crawling is desired.
- ``--y``   The range of years from which data is desired. The first year must be lower than the second. You can only provide one year.
- ``--extended``   A flag indicating whether to use the extended crawler.
- ``--t``   This serves to indicate the number of threads to be created for crawling the data concurrently. It should be taken into account along with the request limit. If not specified, by default, only one thread is used.
- ``--no_key``  A flag indicating whether to perform crawling without using the Semantic Scholar API KEY. It is not recommended to use this option, as the request limit can easily be exceeded. If this option is activated, crawling will always be done with only one thread, even if more are specified with the --t argument.
- ``--citations``     A flag indicating whether to use the citations crawler.

The arguments ``--c`` and ``--y`` must be provided mandatory. The arguments ``--extended`` and ``--citations`` only indicate which crawler to use. If neither of the above two parameters is specified, the **base crawler** will be used as default.

# :file_folder: Data Directory

In this folder, the data obtained through the crawler will be stored. All data is saved in JSON files.

This directory contains three other directories, ``base_crawler_data``, ``extended_crawler_data`` and ``citations_crawler_data``. Inside each of these directories are the JSON files that store the dates extracted with the crawlers.

## :open_file_folder: Base Crawler Data

In this directory, the JSON files obtained using the base crawler are stored. If the extended crawler is used, files will also be placed in this directory.

The data files in these directories have this naming format ``{conf}_base_data.json``, and the data follows this format:

```json
{
    "20XX": [
        {
            "Title": "The title here",
            "Year": "20XX",
            "DOI Number": "10.1111/12345.12345",
            "OpenAlex Link": "https://api.openalex.org/works/", 
            "Authors and Institutions": [
                {
                    "Author": "Author Name 1",
                    "Institutions": [
                        {
                            "Institution Name": "Institution Name here",
                            "Country": "Country Code ISO-2 here"
                        }
                    ]
                },
                {
                    "Author": "Author Name 2",
                    "Institutions": [
                        {
                            "Institution Name": "Institution Name here",
                            "Country": "Country Code ISO-2 here"
                        }
                    ]
                }
            ],
            "Referenced Works": [
                "W1234567890",
                "W1234567890",
                "W1234567890"
            ]
        }
    ]
}
```

## :open_file_folder: Extended Crawler Data

The data files in these directories have this naming format ``{conf}_extended_data.json``, and the data follows this format:

```json
{
    "20XX": [
                {
                "Title": "Paper title here",
                "Year": "20XX",
                "DOI Number": "10.1111/12345.12345",
                "OpenAlex Link": "https://api.openalex.org/works/",
                "S2 Paper ID": "abcdefghijklmnopqrstuvwxyz0123456789",
                "Authors and Institutions": [
                    {
                        "Author": "Author Name 1",
                        "Institutions": [
                            {
                                "Institution Name": "Institution Name here",
                                "Country": "Country Code ISO-2 here"
                            }
                        ]
                    },
                    {
                        "Author": "Author Name 2",
                        "Institutions": [
                            {
                                "Institution Name": "Institution Name here",
                                "Country": "Country Code ISO-2 here"
                            }
                        ]
                    }
                ],
                "Referenced Works": [
                    "W1234567890",
                    "W1234567890",
                    "W1234567890",
                ],
                "Citations S2": [
                    {
                        "paperId": "12345678910abcdefghijklmnopqrstuvwxyz",
                        "title": "Cited paper title here"
                    },
                    {
                        "paperId": "12345678910abcdefghijklmnopqrstuvwxyz",
                        "title": "Cited paper title here"
                    },
                    {
                        "paperId": "12345678910abcdefghijklmnopqrstuvwxyz",
                        "title": "Cited paper title here"
                    },
                ],
                "Abstract": "Paper abstract here",
                "TLDR": "Semantic Scholar TLDR here"
            },
    ]
}
```

## :open_file_folder: Citations Crawler Data

In this directory, the JSON files obtained using the citations crawler are stored. If the extended crawler is used, files will also be placed in this directory.

The data files in these directories have this naming format ``{conf}_citations_data.json``, and the data follows this format:

```json
{
    "Title Paper Citing 1": [
        {
            "Title": "Title Cited Paper 1",
            "Authors": [
                {
                    "Author": "Author Name 1",
                    "Institutions": [
                        {
                            "Institution Name": "Institution Name here",
                            "Country": "Country Code ISO-2 here"
                        }
                    ]
                },
                {
                    "Author": "Author Name 2",
                    "Institutions": [
                        {
                            "Institution Name": "Institution Name here",
                            "Country": "Country Code ISO-2 here"
                        }
                    ]
                }
            ],
            "Venue": "Venue Name here",
            "Year": 1234
        },
        {
            "Title": "Title Cited Paper 2",
            "Authors": [
                {
                    "Author": "Author Name 1",
                    "Institutions": [
                        {
                            "Institution Name": "Institution Name here",
                            "Country": "Country Code ISO-2 here"
                        }
                    ]
                },
            ],
            "Venue": "Venue Name here",
            "Year": 1234
        } 
    ],
}
```

# :newspaper: Log Folder

In this folder, we find two files, ``log_config.py`` is responsible for configuring the log, and ``log_file.log`` will store information about any possible errors that may occur during the execution of the crawler. They can be modified to adapt them to each user's needs.

# :dart: Adding a new conference

If you want to crawl a certain conference, you need to simply go to dblp and search for the conference.
Then you will have to extract the name that this conference has on its link.

For example:

``dblp.org/db/conf/<THIS_IS_THE_NAME_YOU_WILL_NEED>/index.html``

``https://dblp.org/db/conf/middleware/index.html`` for Middleware is simply middleware``

``https://dblp.org/db/conf/cloud/index.html``  for Socc (Symposium on Cloud Computing) is cloud``

> :bangbang: **We also need to consider the link that contains the papers for each year because there are conferences where the name changes in this link. Therefore, the ``verify_link`` function located in the ``basic_crawler.py`` file should be modified to include a condition that takes into account this new name. SoCC presents this case, as it needs to be searched with the name 'cloud', as shown above, but for this link, it needs to be searched by the name 'socc'.**
