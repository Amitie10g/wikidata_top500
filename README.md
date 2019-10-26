# TOP500 importer
![Logo](https://raw.githubusercontent.com/Amitie10g/wikidata_top500/master/logo.png)

**TOP500 importer** (aka. **Wikidata TOP500**) is a project aimed to make a bot to save the [TOP500](https://top500.org) supercomputer database into [Wikidata](https://wikidata.org), using [**Pywikibot**](https://github.com/wikimedia/pywikibot). This branch has support for Redis and has specific support for running under [Toolforge](https://wikitech.wikimedia.org/wiki/Portal:Toolforge/About_Toolforge).

As the TOP500 website lacks a REST API, data is obtained directly from the HTML page, and extracted using the [**Beautiful Soup**](https://pypi.org/project/BeautifulSoup4/) library. So, its base code can be used for any database in HTML-only format, too.

## Software required
* **Python 3.5** or above
* [**Pywikibot**](https://github.com/wikimedia/pywikibot) (included as submodule)
* [**Requests**](https://pypi.org/project/requests/)
* [**Beautiful Soup 4**](https://pypi.org/project/BeautifulSoup4)
* [**Redis**](https://pypi.org/project/redis)

## Does
* Login
* Read settings from command line parameters
* Get data from TOP500
  * Parse the contents from the TOP500 main table (right values and units)
  * Parse the contents from the TOP500 Ranking table
* Submit data to Wikidata. Properties are:
  * Manufacturer
  * Memory
  * Number of cores
  * Power
  * Operating system
  * Performance, in FLOPS, using qualifiers for:
    * Has role: Rmax and Rpeak
    * Date
    * For Rank, I'm finding a property; I would request a new one
* Able to run multiple instances in paralell by adding a ultipler at the end of the comand in ``--mass`` mode.
* Check if some property has been already set, and don't commit.
* Mass import

## TODO
* <s>Commit everything at once, if technically possible.</s> Items are imported one at time.
* For properties with multiple values (eg. multiple manufacturers), got as a list and commit at once, I haven´t checked yet.

## Downloading and installing
* Install the dependencies.
  ```
  pip3 install beautifulsoup4 redis requests
  ```

* Download:
  ```
  git clone \
      --recurse-submodules \
      --shallow-submodules \
      https://github.com/Amitie10g/wikidata_top500.git
  ```

* Edit ``config.py`` as you need (if you're using another Wikibase instance).

## Running
* ``python3 pywikibot/pwb.py main.py -i <Wikidata item> -t <TOP500 id>`` for individual import.
* ``python3 pywikibot/pwb.py main.py --mass <num>`` for mass import.
* For the first time, you need to set up pywikibot, in order to login:

  ```
  python3 pywikibot/pwb.py pywikibot/generate_user_files.py
  chmod 600 user-config.py user-password.py
  ```

### Notes
* ``run.sh`` is a shell script designed specifically to be used at Toolforge. Currently, is is used for mass-import.
* For mass update of already-existing items, several ``./main.py -i <Wikidata item> -t <TOP500 id>`` instances may be ran in parallel.
* Using your main account is strongly discouraged. Use a [bot account](https://www.wikidata.org/wiki/Wikidata:Bots) with a [bot password](https://www.wikidata.org/wiki/Special:BotPasswords).

## Footnotes

*The scripts contained in this project has been released into the **MIT License***
