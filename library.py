# -*- coding: utf-8 -*-
"""
TOP500 importer (aka. Wikidata TOP500) is a project aimed to make a bot
to save the TOP500 supercomputer database into Wikidata, using Pywikibot.

Copyright (c) 2019 Davod (Amitie 10g)

Licensed under the MIT license. See LICENSE for details
"""

# :: Standard libraries
import re
import sys
import json
import decimal
import datetime
import subprocess

# :: Third party library
import redis
import requests
from bs4 import BeautifulSoup
import pywikibot

# :: Local dictionaries
import slist

class Top500Importer:
    """This is the TOP500 importer class."""

    def __init__(self, wiki_site, wiki_lang, redis_server, redis_port, instance_of, top500url, log_page, status_page):
        """Parameters
        ----------
        wiki_site : str
            The Wikibase sitename.
        wiki_lang : str
            The Wikibase language.
        redis_server : str
            The Redis server address.
        redis_port : int
            The Redis swerver port.
        instance_of : str
            The "Instance of" property.
        top500url : str
            The TOP500 URL.
        log_page : str
            The Wikibase log page.
        status_page : str
            The Wikibase status page.
        """

        # :: Set variables
        self.wiki_site = wiki_site
        self.wiki_lang = wiki_lang
        self.redis_server = redis_server
        self.redis_port = redis_port
        self.instance_of = instance_of
        self.top500url = top500url
        self.log_page = log_page
        self.status_page = status_page

        # :: If something went wrong, set self.error variable
        try:
            self.redis = redis.Redis(host=self.redis_server, port=self.redis_port, db=0)
            self.site = pywikibot.Site(self.wiki_site, self.wiki_lang)
        except (redis.ConnectionError, pywikibot.exceptions.SiteDefinitionError) as e:
            self.error = e

    # :: Instance methods

    def getTOP500Data(self, identifier):
        """Parse the TOP500 contents into a dictionary (array) using BeautifulSoup4.

        Parameters
        ----------
        identifier : str
            The TOP500 system identifier.

        Returns
        -------
        dict
            The contents from page as list.
        """

        # Note: Only critical errors will be printed

        # Check if the identifier string integer-like (0-9)
        try:
            identifier = str(identifier)
            if re.search('^[0-9]+$', str(identifier)) is None:
                raise ValueError('Error: Wrong value for identifier.')
        except ValueError as e:
            sys.stderr.write(str(e) + '\n')
            return False

        # Check if able to load from Redis
        try:
            data = json.loads(self.redis.get('top500-sys-' + identifier))

        # If unable to load from Redis, get from the web normally
        except (json.JSONDecodeError, redis.exceptions.RedisError, AttributeError, TypeError):
            # Get data from TOP500 page
            try:
                r = requests.get(self.top500url + '/system/' + identifier)

                # Check if request returns HTTP status code 200; return False if not.
                if r.status_code != 200:
                    raise ValueError(u'Notice: System not found.')
            except (ValueError, requests.exceptions.RequestException) as e:
                #sys.stderr.write(str(e) + '\n')
                return False

            # Parse the raw text from the Request object
            top500rawdata = r.text
            top500soup = BeautifulSoup(top500rawdata, 'html.parser')

            # Get the platform (title)
            title = ''.join(top500soup.find("h1").get_text().replace("\n", '')).strip().split(' - ')

            name = title[0]
            try:
                platform = title[1].split(', ')[0]

            except (ValueError, IndexError):
                platform = ''

            # Extract data from the main table
            maintable = top500soup.find("table", attrs={"class":"table-condensed"})

            mainheaders = []
            for row in maintable.find_all("tr")[0:]:
                th = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(':', '') for td in row.find_all("th")]
                mainheaders.append(''.join(th))

            maindata = {}
            i = 0
            for row in maintable.find_all("tr")[0:]:
                dataset = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(', ', '') for td in row.find_all("td")]
                maindata.update({mainheaders[i]:''.join(dataset)})
                i = i+1

            # Extract data from the Rank table
            table2 = top500soup.find("table", attrs={"class":"table-responsive"})

            rankheaders = []
            for row in table2.find_all("tr")[0:]:
                th = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(':', '') for td in row.find_all("th")]
                rankheaders.append(th)

            rankheaders = rankheaders[0]
            rankdata = []
            for row in table2.find_all("tr")[1:]:
                td = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(', ', '') for td in row.find_all("td")]

                j = 0
                rowdata = {}
                for cell in td:
                    rowdata.update({rankheaders[j]:cell.strip()})
                    j = j+1
                rankdata.append(rowdata)

            # Merge the data into the final dictionary
            data = {}
            data.update({'ID':identifier})
            data.update({'Title':name, 'Platform':platform})
            data.update(maindata)
            data.update({'Rank':rankdata})

            # Attemp to save into Redis server
            try:
                self.redis.set('top500-sys-' + identifier, json.dumps(data))

            except (redis.exceptions.RedisError, AttributeError):
                pass

        return data

    def getTOP500SiteData(self, identifier):
        """Get site (location) available at https://www.top500.org/site/id
        Designed to be used inside a while loop.

        Parameters
        ----------
        identifier : str
            The TOP500 site identifier.

        Returns
        -------
        dict
            The data found at the site (location) page.
        """

        # Check if the identifier string integer-like (0-9)
        try:
            identifier = str(identifier)
            if re.search('^[0-9]+$', identifier) is None:
                raise ValueError('Error: Wrong value for identifier.')
        except ValueError as e:
            sys.stderr.write(str(e) + '\n')
            return False

        try:
            data = self.redis.get('top500-loc-' + identifier).decode("utf-8")
            data = json.loads(data)
        except (json.JSONDecodeError, redis.exceptions.RedisError):
            # Get data from TOP500 page
            r = requests.get(self.top500url + '/system/' + identifier)
            if r.status_code != 200:
                return False

            top500rawdata = r.text
            top500soup = BeautifulSoup(top500rawdata, 'html.parser')

            # Get the title
            title = ''.join(top500soup.find("title").get_text().replace("\n", '')).strip().split(' | ')

            # Extract data from the main table
            maintable = top500soup.find("table", attrs={"class":"table-condensed"})

            mainheaders = []
            for row in maintable.find_all("tr")[0:]:
                th = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(':', '') for td in row.find_all("th")]
                mainheaders.append(''.join(th))

            maindata = {}
            i = 0
            for row in maintable.find_all("tr")[0:]:
                dataset = [re.sub(r'\s\s+', ' ', td.get_text()).strip().replace(', ', '') for td in row.find_all("td")]
                maindata.update({mainheaders[i]:''.join(dataset)})
                i = i+1

            data = {}
            data.update({'ID':identifier})
            data.update({'Title':title[0]})
            data.update(maindata)

            try:
                self.redis.set('top500-loc-' + identifier, json.dumps(data))
            except redis.exceptions.RedisError:
                pass

        return data

    def addClaim(self, item, claim, data, datatype='string', nonempty=True):
        """Add a claim/qualifier to a statement.

        Parameters
        ----------
        item : str
            The item to be edited.
        claim : str
            The claim (property) to be added.
        data : mixed
            The value for the claim.
            If you want to add qualifiers, you should format as list. The first key
            contains the value; the second key contains a dict (associative array)
            with pairs of Qualifier=>Value. Possible qualifiers are (see datatype):

            * 'has_role', as 'statement' datatype

            * 'date', as 'date' datatype
        datatype : str
            The desired data type. Possible values are:

            * 'statement', Wikidata statement

            * 'ammount', for numeric values added as ammount, with units (optional)

            * 'date', in format mm/dd/YYYY. Parsing more format is planned

            * 'string', plain string not associated with a statement
        nonempty : bool
            If want or not to write a property already set (to avoid duplicates):

            * False (default): don't write

            * True: write anyway

        Returns
        -------
        mixed
            True if the item has been updated;
            Pagename if the item has been created;
            False if something fails.
        """

        # Note: Non-critical exceptions printing are commented.

        stripped = lambda s: "".join(i for i in s if 31 < ord(i) < 127)

        summary = 'edited using [[:d:User:TOP500 importer|TOP500 importer]]'

        # :: Validate data

        # Validate property
        try:
            claim = self.str2prop(claim)
            if not claim:
                raise ValueError(u'Error: Unknown property provided.')
        except ValueError as e:
            sys.stderr.write(str(e) + '\n')
            return False

        # Check if data contains qualifiers
        if isinstance(data, list):
            value = data[0]
            qualifiers = data[1]
        else:
            value = data
            qualifiers = False

        # Create item
        if item == 'Q0':
            try:
                item = pywikibot.ItemPage(self.site)
                item.editLabels(labels=data, summary=summary)
                item = item.getID()
                return item
            except ValueError as e:
                sys.stderr.write(str(e) + '\n')
                return False
            except (pywikibot.exceptions.PageRelatedError,
                    pywikibot.exceptions.WikiBaseError,
                    pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error,
                    pywikibot.exceptions.ServerError) as e:
                sys.stderr.write(str(e) + '\n')
                return False
        else:
            try:
                repo = self.site.data_repository()
                item = pywikibot.ItemPage(repo, item)
            except (pywikibot.exceptions.PageRelatedError,
                    pywikibot.exceptions.WikiBaseError,
                    pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error,
                    pywikibot.exceptions.ServerError) as e:
                sys.stderr.write(str(e) + '\n')
                return False

        # Check if claim has been set already
        if nonempty:
            try:
                claims = item.get(u'claims')
                if claim in claims[u'claims']:
                    raise ValueError(u'Notice: Claim already set: ' + stripped(str(claim)))
            except ValueError as e:
                #sys.stderr.write(str(e) + '\n')
                return False

        # :: Set claim

        try:
            claim = pywikibot.Claim(repo, claim)
        except (pywikibot.exceptions.PageRelatedError,
                pywikibot.exceptions.WikiBaseError,
                pywikibot.exceptions.TimeoutError,
                pywikibot.exceptions.Server504Error,
                pywikibot.exceptions.ServerError) as e:
            sys.stderr.write(str(e) + '\n')
            return False

        # :: Set target

        # Statement (QXXX)
        if datatype == 'statement':
            try:
                value = self.str2statement(stripped(str(value)))
                if not value:
                    raise ValueError(u'Error: Unknown statement provided!\n')
                claim.setTarget(pywikibot.ItemPage(repo, value))
            except ValueError:
                #sys.stderr.write(str(e) + '\n')
                return False
            except (pywikibot.exceptions.PageRelatedError,
                    pywikibot.exceptions.WikiBaseError,
                    pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error,
                    pywikibot.exceptions.ServerError) as e:
                sys.stderr.write(str(e) + '\n')
                return False

        # Amount (123.45 <suffix>)
        elif datatype == 'amount':
            try:
                if not value:
                    raise ValueError(u'Notice: Empty value.')
                value = value.split(' ')
                amount = self.formatDecimal(value[0])
                if not amount:
                    raise ValueError(u'Error: Non-numeric value provided!')
            except ValueError as e:
                #sys.stderr.write(str(e) + '\n')
                return False

            if len(value) > 1:
                try:
                    entity_helper_string = "http://www.wikidata.org/entity/"
                    unit = self.str2statement(value[1])
                    if not unit:
                        raise ValueError(u'Error: Invalid ammount and/or unit provided!')
                    unit = entity_helper_string + unit
                    claim.setTarget(pywikibot.WbQuantity(amount=amount, unit=unit, site=self.site))
                except ValueError as e:
                    #sys.stderr.write(str(e) + '\n')
                    return False
                except (pywikibot.exceptions.PageRelatedError,
                        pywikibot.exceptions.WikiBaseError,
                        pywikibot.exceptions.TimeoutError,
                        pywikibot.exceptions.Server504Error,
                        pywikibot.exceptions.ServerError) as e:
                    sys.stderr.write(str(e) + '\n')
                    return False
            else:
                try:
                    claim.setTarget(pywikibot.WbQuantity(amount=amount, site=self.site))
                except ValueError as e:
                    #sys.stderr.write(str(e) + '\n')
                    return False
                except (pywikibot.exceptions.PageRelatedError,
                        pywikibot.exceptions.WikiBaseError,
                        pywikibot.exceptions.TimeoutError,
                        pywikibot.exceptions.Server504Error,
                        pywikibot.exceptions.ServerError) as e:
                    sys.stderr.write(str(e) + '\n')
                    return False

        # Date (12/2018)
        elif datatype == 'date':
            try:
                date = self.getDate(value)
                if not date:
                    raise ValueError(u'Error: Invalid date provided!')
                claim.setTarget(pywikibot.WbTime(year=date[0], month=date[1]))
            except ValueError:
                #sys.stderr.write(str(e) + '\n')
                return False
            except (pywikibot.exceptions.PageRelatedError,
                    pywikibot.exceptions.WikiBaseError,
                    pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error,
                    pywikibot.exceptions.ServerError) as e:
                sys.stderr.write(str(e) + '\n')
                return False

        # String ("anything")
        else:
            try:
                claim.setTarget(stripped(str(value)))
            except ValueError as e:
                #sys.stderr.write(str(e) + '\n')
                return False
            except (pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error,
                    pywikibot.exceptions.ServerError) as e:
                sys.stderr.write(str(e) + '\n')
                return False

        # :: Add claim

        try:
            item.addClaim(claim, summary=summary)
        except (pywikibot.exceptions.PageRelatedError,
                pywikibot.exceptions.WikiBaseError,
                pywikibot.exceptions.TimeoutError,
                pywikibot.exceptions.Server504Error,
                pywikibot.exceptions.ServerError) as e:
            sys.stderr.write(str(e) + '\n')
            return False

        # :: Qualifiers

        if qualifiers is not False:
            for qualifier_key, qualifier_value in qualifiers.items():
                try:
                    prop = self.str2prop(qualifier_key)
                    if not prop:
                        raise ValueError(u'Error: Unknown property provided!')
                    qualifier = pywikibot.Claim(repo, prop)
                except (ValueError, pywikibot.exceptions.WikiBaseError) as e:
                        #sys.stderr.write(str(e) + '\n')
                    continue
                except (pywikibot.exceptions.PageRelatedError,
                        pywikibot.exceptions.TimeoutError,
                        pywikibot.exceptions.Server504Error) as e:
                    sys.stderr.write(str(e) + '\n')
                    return False

                if qualifier_key == 'has_role':
                    try:
                        statement = self.str2statement(stripped(str(qualifier_value)))
                        if not statement:
                            raise ValueError(u'Error: \'has_role\' statement not set!')
                        qualifier.setTarget(pywikibot.ItemPage(repo, statement))
                    except (ValueError, pywikibot.exceptions.WikiBaseError) as e:
                        #sys.stderr.write(str(e) + '\n')
                        continue
                    except (pywikibot.exceptions.PageRelatedError,
                            pywikibot.exceptions.TimeoutError,
                            pywikibot.exceptions.Server504Error) as e:
                        sys.stderr.write(str(e) + '\n')
                        return False

                elif qualifier_key == 'date':

                    try:
                        date = self.getDate(qualifier_value)
                        if not date:
                            raise ValueError(u'Error: Invalid date provided for qualifier!\n')
                        qualifier.setTarget(pywikibot.WbTime(year=int(date[0]), month=int(date[1])))
                    except (ValueError, pywikibot.exceptions.WikiBaseError) as e:
                        #sys.stderr.write(str(e) + '\n')
                        continue
                    except (pywikibot.exceptions.PageRelatedError,
                            pywikibot.exceptions.TimeoutError,
                            pywikibot.exceptions.Server504Error) as e:
                        sys.stderr.write(str(e) + '\n')
                        return False

                else:
                    try:
                        qualifier.setTarget(qualifier_value)
                    except (ValueError, pywikibot.exceptions.WikiBaseError) as e:
                        #sys.stderr.write(str(e) + '\n')
                        continue
                    except (pywikibot.exceptions.PageRelatedError,
                            pywikibot.exceptions.TimeoutError,
                            pywikibot.exceptions.Server504Error) as e:
                        sys.stderr.write(str(e) + '\n')
                        return False

                try:
                    claim.addQualifier(qualifier, summary=summary)
                except (ValueError, pywikibot.exceptions.WikiBaseError) as e:
                    #sys.stderr.write(str(e) + '\n')
                    continue
                except (pywikibot.exceptions.PageRelatedError,
                        pywikibot.exceptions.TimeoutError,
                        pywikibot.exceptions.Server504Error) as e:
                    sys.stderr.write(str(e) + '\n')
                    return False

        return True

    def updateItem(self, data, item='Q0', updatelog=True):
        """Update an item.

        Parameters
        ----------
        item : str
            The Wikidata item to be edited. If no item provided, new one will be created.
        data : dict
            The data retrived from getTOP500Data().

        Returns
        -------
        bool
            True if successful, False if fails.
        """

        if bool(re.search('^Q[0-9]+$', item)) is None:
            return False

        if item == 'Q0':
            print(u'Creating new item...\n')
            try:
                item = self.addClaim(item, 'label', {'en':data['Title'], 'es':data['Title']}, 'label')
                if not item:
                    raise ValueError(u'Error: Something went wrong when creating a new item')
            except (ValueError, IndexError) as e:
                sys.stderr.write(str(e) + '\n')
                return False

        # Instance of
        print(u'\nInstance of...')
        try:
            self.addClaim(item, 'instance_of', self.instance_of, 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Manufacturer
        print(u'\nManufacturer...')
        try:
            self.addClaim(item, 'manufacturer', data['Manufacturer'], 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Site
        print(u'\nSite...')
        try:
            self.addClaim(item, 'site', data['Site'], 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Cores
        print(u'\nCores...')
        try:
            self.addClaim(item, 'cores', data['Cores'], 'amount')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Memory
        print(u'\nMemory...')
        try:
            self.addClaim(item, 'memory', data['Memory'], 'amount')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # CPU
        print(u'\nCPU...')
        try:
            self.addClaim(item, 'cpu', data['Processor'], 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Bus (not available at Wikidata yet, see Wikidata:Property_proposal/bus)
        #print(u'\nBus...')
        #try:
            #self.addClaim(item, 'bus', [data['bus'], {'has_role':'interconnect'}], 'statement')
        #except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            #pass

        # Power
        print(u'\nPower...')
        try:
            self.addClaim(item, 'power', data['Power Consumption'], 'amount')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Operating sistem
        print(u'\nOS...')
        try:
            self.addClaim(item, 'os', data['Operating System'], 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Platform
        print(u'\nPlatform...')
        try:
            self.addClaim(item, 'platform', data['Platform'], 'statement')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Top500 ID
        print(u'\nTop500 ID...')
        try:
            self.addClaim(item, 'top500identifier', data['ID'], 'string')
        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Performance (loop)
        print(u'\nPerformance...')
        try:
            for rankdata in data['Rank']:
                date = rankdata['List']

                try:
                    rmax = rankdata['Rmax (GFlops)'] + ' GFlops'
                    rpeak = rankdata['Rpeak (GFlops)'] + ' GFlops'
                except (ValueError, IndexError):
                    try:
                        rmax = rankdata['Rmax (TFlops)'] + ' TFlops'
                        rpeak = rankdata['Rpeak (TFlops)'] + ' TFlops'
                    except (ValueError, IndexError):
                        try:
                            rmax = rankdata['Rmax (PFlops)'] + ' PFlops'
                            rpeak = rankdata['Rpeak (PFlops)'] + ' PFlops'
                        except (ValueError, IndexError):
                            #sys.stderr.write(str(e) + '\n')
                            pass

                try:
                    self.addClaim(item, 'performance', [rmax, {'has_role':'rmax', 'date':date}], 'amount', False)
                    self.addClaim(item, 'performance', [rpeak, {'has_role':'rpeak', 'date':date}], 'amount', False)
                except (ValueError, IndexError) as e:
                    #sys.stderr.write(str(e) + '\n')
                    pass

        except (ValueError, IndexError) as e:
            #sys.stderr.write(str(e) + '\n')
            pass

        # Once everything done, log
        if updatelog:
            self.updateLog(item)

        return True

    def updateStatus(self, status=0):
        """Update status page.

        Parameters
        ----------
        status : int
            The status:

             * 0: stopped

             * 1: running

             * 2: error (if something went wrong)

        Returns
        -------
        object
            pywikibot.Page.save() result: True if successful; False if fails.
        """

        summary = 'update bot status: '

        if status == 0:
            summary = summary + 'running'
        elif status == 2:
            summary = summary + 'stopped'
        elif status == 128:
            summary = summary + 'ended one'
        elif status == 1:
            summary = summary + 'error'

        try:
            page = pywikibot.Page(self.site, self.status_page)
            page.text = str(status)
            return page.save(summary=summary, minor=True)
        except (NameError, AttributeError):
            return False
        except (pywikibot.exceptions.PageRelatedError,
                pywikibot.exceptions.WikiBaseError,
                pywikibot.exceptions.TimeoutError,
                pywikibot.exceptions.Server504Error) as e:
            sys.stderr.write(str(e) + '\n')
            return False

    def getLog(self):
        """Get the contents from Log page.

        Parameters
        ----------
        void

        Returns
        -------
        string
            Page contents (as wikitext).
        """

        try:
            page = pywikibot.Page(self.site, self.log_page)
            return page.get()
        except (pywikibot.exceptions.PageRelatedError,
                pywikibot.exceptions.WikiBaseError,
                pywikibot.exceptions.TimeoutError,
                pywikibot.exceptions.Server504Error) as e:
            sys.stderr.write(str(e) + '\n')
            return False

    def updateLog(self, item):
        """Save logs when item is updated.

        Parameters
        ----------
        item : str
            The Wikidata item to be edited. If no item provided, new one will be created.

        Returns
        -------
        bool
            pywikibot.Page.save() result: True if successful; False if fails.
        """

        tries = 3
        for i in range(tries):
            try:
                page = pywikibot.Page(self.site, self.log_page)
                page.text = page.text.replace('<!-- End List -->', '') + '* {{q|' + item + "}}\n<!-- End List -->\n"
                summary = 'Item [[' + item + ']] successfuly updated'
                return page.save(summary=summary, minor=True)
            except (pywikibot.EditConflict,
                    pywikibot.exceptions.TimeoutError,
                    pywikibot.exceptions.Server504Error) as e:
                if i < tries - 1: # i is zero indexed
                    continue

                sys.stderr.write(str(e) + '\n')
                return False
            except (pywikibot.OtherPageSaveError,
                    pywikibot.exceptions.WikiBaseError) as e:
                sys.stderr.write(str(e) + '\n')
                return False
            break

    def main(self, identifier, item):
        """Main function, to fill individual items, if already exist.

        Parameters
        ----------
        id : str
            The TOP500 system identifier.
        item : str
            The Wikidata item.

        Returns
        -------
        bool
            True if successful, False if fails.
        """

        try:
            data = self.getTOP500Data(identifier)
            if not data:
                raise ValueError('Error: No data found!')

            try:
                if not self.updateItem(data, item, False):
                    raise ValueError('Error: Something went wrong when updating!')
            except ValueError as e:
                sys.stderr.write(str(e) + '\n')
                return False
        except ValueError as e:
            sys.stderr.write(str(e) + '\n')
            return False

        return True

    def mass(self, mul=0):
        """Create items with data in masse.

        Parameters
        ----------
        void

        Returns
        -------
        void
        """

        fact = 2000

        try:
            mul = int(mul)
        except (ValueError, NameError):
            mul = 0

        try:
            identifier = self.readCounter(mul)
            if not identifier:
                raise ValueError
        except ValueError:
            identifier = int((mul*fact)+1)

        limit = int(((mul*fact)+1)+fact)

        while identifier < limit:

            print(u'Debug: ID: ' + str(identifier) + "\n")

            try:
                data = self.getTOP500Data(str(identifier))

                if not data:
                    raise ValueError

                try:
                    if self.updateItem(data):
                        self.updateCounter(identifier, str(mul))

                    else:
                        raise ValueError('Something went wrong when updating.')

                except ValueError as e:
                    sys.stderr.write(str(e) + '\n')
                    self.updateCounter(identifier, str(mul))

            except ValueError:
                self.updateCounter(identifier, str(mul))

            identifier = identifier + 1

        return True

    # :: Static methods

    @staticmethod
    def getDate(date):
        """Validate the date, in TOP500 Rank table format (mm/YYYY),
        and return the month and year.

        Parameters
        ----------
        date : str
            The date to be parsed.

        Returns
        -------
        list
            The list with month ([1]) and year([0]); False if fails.
        """

        try:
            datetime.datetime.strptime(date, '%m/%Y')
            date = date.split('/')
            return [date[1], date[0]]

        except (ValueError, IndexError):
            return False

    @staticmethod
    def formatDecimal(num):
        """Normalize decimal numbers, remove trailing zeroes
        (credits: https://stackoverflow.com/questions/2440692).

        Parameters
        ----------
        num : mixed
            The number (string or numeric) to be parsed.

        Returns
        -------
        Decimal
            The number as Decimal value, with trailing zeroes removed.
        """

        try:
            dec = decimal.Decimal(str(num))
            return dec.quantize(decimal.Decimal(1)) if dec == dec.to_integral() else dec.normalize()

        except decimal.InvalidOperation:
            return False

    @staticmethod
    def str2statement(statement):
        """Parse arbitrary string into a Wikidata statement.

        Parameters
        ----------
        statement : str
            The string to be parsed.

        Returns
        -------
        str
            The equivalent statement.
        """

        return slist.statements.get(str(statement), False)

    @staticmethod
    def str2prop(prop):
        """Parse arbitrary string into a Wikidata property.

        Parameters
        ----------
        prop : str
            The string to be parsed.

        Returns
        -------
        str
            The equivalent property.
        """

        if prop == 'label':
            return 'label'

        return slist.properties.get(str(prop), False)

    @staticmethod
    def identifier2url(prop):
        """Parse a given identifier value and property, and get the URL.

        Parameters
        ----------
        prop : str
            The property (PXXXX) to be parsed.

        Returns
        -------
        str
            The desired URL.
        """

        return slist.identifiers.get(str(prop), False)

    @staticmethod
    def updateCounter(amount, mul=1):
        """Update the counter, in both internal and Wiki.

        Parameters
        ----------
        id : int
            The amount.

        Returns
        -------
        bool
            pywikibot.Page.save() result: True if successful; False if fails.
        """

        try:
            f = open("masscount."+str(mul), "w")
            f.write(str(amount))
            f.close()
            return True
        except (OSError, IOError) as e:
            sys.stderr.write(str(e) + '\n')
            return False

    @staticmethod
    def readCounter(mul):
        """Read the identifier counter from local file.

        Parameters
        ----------
        mul: int
            The multiplier.

        Returns
        -------
        int
            The identifier; False otherwise.
        """
        try:
            f = open("masscount."+str(mul), "r")
            identifier = f.read()
            f.close()
            return int(identifier)
        except (ValueError, OSError, IOError):
            return False

    @staticmethod
    def qstat():
        """Run qstat and return its status.

        Parameters
        ----------
        void

        Returns
        -------
        int
            The return status.
        """
        return subprocess.run(["qstat", "-j", "top500importer*"], stdout=subprocess.DEVNULL, check=True)
