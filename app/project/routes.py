import feedparser
import os
import csv
from collections import Counter
import re
import json
from datetime import datetime
import warnings
from flask import Flask, render_template, request, url_for, redirect, request, Blueprint, session, flash
import urllib
from flask_assets import Environment, Bundle
from flask_login import current_user
from flask import current_app as app
from .models import db, User
from flask_login import login_required
from shutil import copyfile
from .forms import ChangePasswordForm, ChangeUsernameForm
from werkzeug.security import generate_password_hash, check_password_hash

feeds_json_path = "feeds.json" #Define the path to the JSON file containing RSS feed URLS and outlet names.
default_feeds_json_path = "default_feeds.json"
blacklist_path = "word_blacklist" #Define the path to the list of blacklisted common words.
default_blacklist_path = os.path.join(app.root_path,"default_blacklist") #Define the path to the default list of blacklisted common words.
archive_path = "archive" #Define the path to the directory containing archived RSS data.
issues_json_path = "tracked_issues.json" #Define the path to the tracked issues.
default_issues_json_path = "default_issues.json"
messages_path = "messages.json"
all_messages_path = os.path.join(app.root_path,"all_messages.json")
alerts_path = "alerts.json"

# Blueprint Configuration
main_bp = Blueprint('main_bp', __name__ ,
                    template_folder='templates',
                    static_folder='static')
#assets = Environment(app)

#   \brief - Flash validation errors if validation fails for a form.

#   \param form - The form object for which validation has failed.

def flash_form_errors(form):
    for field, error_messages in form.errors.items():
        for err in error_messages:
            flash(err)

#   \brief - Converts a local path from the project root into an absolute path.

#   \param - The local path.

#   \returns - The absolute path.

def create_funcroot(path):
    funcroot = os.path.join(app.root_path,"users",str(current_user.id),path)
    if not os.path.exists(funcroot):
        os.makedirs(funcroot)
    return funcroot

#   \brief - Reads a JSON file into a dictionary.

#   If there is no file at the specified path, a blank dictionary is created.

#   \param json_path - The path to the file where the JSON data is to be obtained from.
#   \param is_dict - True if the root data type is a dictionary. False if it is a list.
#   \param relative_path - True if the path is relative from the user's directory.

#   \returns - The JSON data as a dictionary.


def read_json(json_path,is_dict=True,relative_path=True):
    if relative_path:
        funcroot = create_funcroot("")
    else:
        funcroot = ""
    try:
        json_file = open(os.path.join(funcroot,json_path),"r")
    except FileNotFoundError:
        if is_dict:
            content = {}
        else:
            content = []
    else:
        content = json.loads(json_file.read())
        json_file.close()
    return content

#   \brief - Saves a dictionary in JSON format to an external file.

#   \param issues - The dictionary to be saved.
#   \param json_path - The path to the file where the JSON data is to be saved.
#   \param relative_path - True if the path is relative from the user's directory.

def write_json(data,json_path,relative_path=True):
    if relative_path:
        funcroot = create_funcroot("")
    else:
        funcroot = ""
    json_file = open(os.path.join(funcroot,json_path),"w")
    json_file.write(json.dumps(data, sort_keys=True, indent=4))
    json_file.close()
    
#   \brief - Sets the default user's tracked issues and feeds to the defaults.
    
def create_defaults():
    funcroot = create_funcroot("")
    copyfile(os.path.join(app.root_path,default_feeds_json_path),os.path.join(funcroot,default_feeds_json_path))
    copyfile(os.path.join(app.root_path,default_issues_json_path),os.path.join(funcroot,default_issues_json_path))

#   \brief - Saves the data dictionary in JSON format.

#   File name uses format <prefix>-<date>-<time>.json. This is saved in tracker.dat.

#   \param data - The data dictionary containing the RSS data.
#   \param archive_path - The path to the archive directory.
#   \param prefix - The prefix to the archive json file name - eg. "rss data".

def archive_json(data,archive_path,prefix):
    funcroot = create_funcroot(archive_path)
    ts = datetime.now()
    # dd/mm/YY H:M:S
    ts_string = ts.strftime("%d.%m.%Y-%H:%M:%S")
    file_name = prefix+"-"+ts_string+".json"
    write_json(data,os.path.join(archive_path,file_name))
    tracker_file = open(os.path.join(funcroot,"tracker.dat"),"w")
    tracker_file.write(file_name) #Saves the name of the archive file in tracker.dat to be loaded automatically if read_default_archive() is called on the next run.
    tracker_file.close()

#   \brief - Reads a JSON file into a dictionary for use as the RSS data file.

#   \param archive_path - The path to the archive directory.
#   \param file_name - The name of the JSON file to get the RSS data from.

#   \returns - The dictionary that all RSS feed contents has been written to from the JSON file.

def read_archive_json(archive_path,file_name):
    funcroot = create_funcroot(archive_path)
    archive_file = open(os.path.join(funcroot,file_name))
    print("Reading archive \""+file_name+"\"")
    data = json.loads(archive_file.read())
    archive_file.close()
    return data

#   \brief - Reads the most recently generated JSON archive into a dictionary for use as the RSS data file.

#   The name of this file is found in tracker.dat.

#   \param archive_path - The path to the archive directory.

#   \returns - The dictionary that all RSS feed contents has been written to from the JSON file.

def read_default_archive(archive_path):
    funcroot = create_funcroot(archive_path)
    try:
        tracker_file = open(os.path.join(funcroot,"tracker.dat"),"r")
    except FileNotFoundError:
        data = {}
    else:
        data = read_archive_json(archive_path,tracker_file.read())
        tracker_file.close()
    return data

#   \brief - Reads the file of blacklisted common words into a list.

#   \param - Path to list of blacklisted common words.

#   \returns - A list containing the list of blacklisted common words.

def read_blacklist(blacklist_path):
    funcroot = create_funcroot("")
    fullpath = os.path.join(funcroot,blacklist_path)
    if not os.path.exists(fullpath):
        copyfile(default_blacklist_path,fullpath)
    blacklist_file = open(fullpath,"r")
    return blacklist_file.read().split("\n")

#   \brief - Adds a new key and its values to the container dictionary or edits the existing ones for the key.

#   \param container - The dictionary to which the value is to be added.
#   \param name - The name of the key to be tracked or edited.
#   \param vals - The key's new values.

def add_val(container,name,vals):
    vals = [val.strip() for val in vals] #Trim all values.
    container[name] = vals #The values are added to the dictionary under the issue name as their key.

#   \brief - Removes a key from the container dictionary.

#   \param container - The dictionary from which the value is to be removed.
#   \param name - The name of the key to be removed.

def rm_val(container,name):
    try:
        del container[name] #Removes the item from the dictionary.
    except KeyError:
        warnings.warn("Issue \""+name+"\" is not being tracked.") #Issues a warning if the user tries to remove an issue which is not being tracked.

#   \brief - Takes the active default issues/outlets and returns them in a separate dictionary.

#   \param - Defaults - the dictionary of all default issues/outlets.

#   \returns - The active default issues/outlets only.

def get_active_defaults(defaults):
    active_defaults = {}
    for name in defaults.keys():
        if defaults[name][1]:
            active_defaults[name] = defaults[name][0]
    return active_defaults

#   \brief - Removes HTML code from string.

#   \param raw - String from which the HTML code is to be removed.

def clean_html(raw):
    clean_regex = re.compile('<.*?>')
    clean = re.sub(clean_regex, '', raw)
    return clean

#    \brief - Iterates through the JSON of RSS feed URLs and writes all contents to a dictionary.

#    Creates a separate list for each outlet within the dictionary.
    
#   \returns data - The dictionary that all RSS feed contents have been written to.

def get_feeds():
    all_feeds = {**session.get('feeds_list'),**session.get('active_default_feeds')}
    data={} #Creates the local dictionary that RSS data will be written to.
    for outlet in all_feeds:
        data[outlet] = []
        for feed in all_feeds[outlet]:
            try:
                feed_data = feedparser.parse(feed) #Save the RSS feed data.
                feed_data.feed.link #Check that the feed has been saved properly.
            except Exception:
                flash(feed+" is not a working RSS link, skipping.") #Flash this to the user if the try statement fails.
            else:
                trunc_feed_data = []
                for entry in feed_data.entries:
                    entry_data = {}
                    entry_data['title'] = entry.title
                    try:
                        entry_data['summary'] = clean_html(entry.summary)
                    except AttributeError:
                        entry_data['summary'] = ""
                    entry_data['link'] = entry.link
                    try:
                        entry_data['published'] = entry.published
                    except AttributeError:
                        entry_data['published'] = "" #Takes only necessary attributes from stories.
                    trunc_feed_data.append(entry_data)
                data[outlet].append(trunc_feed_data) #Append the data to the list with the key of the name of the outlet in the data dictionary.
    archive_json(data,archive_path,"rss_data") #Archive the rss data.
    return data; #Loops through the list of feed URLS and writes the contents of each respective RSS feed to a dictionary with the feed title has the key, returning this dictionary.

#   \brief - Returns a regular expression object to test if the given word is present as a whole word in the tested string.

#   \param word - The word to be searched for.

#   \returns - A regular expression object to test if the given word is present as a whole word in the tested string.

def whole_word(word):
    return re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search

#   \brief - Returns the search ranking of an entry with respect to the terms supplied.

#   Ranking criteria:
#   Base of 0 (no matches in title or summary).
#   +2 For every term matched in the title.
#   +1 For every term matched in the summary.

#   \param terms - The list of terms to be matched within the entry.
#   \param entry - The entry for the term to be matched with.

#   \returns - The ranking of the entry.

def rank_entries(terms, entry):
    rank = 0
    for term in terms:
        nopunc_term = re.sub(r'[^\w\s]','',term.lower()) #Strips punctuation from the search term and makes it lower case.
        try:
            nopunc_title = re.sub(r'[^\w\s]','',entry['title'].lower()) #Strips punctuation from the title and makes it lower case.
        except KeyError:
            entry['title'] = ""
            nopunc_title = ""
        try:
            nopunc_summary = re.sub(r'[^\w\s]','',entry['summary'].lower()) #Strips punctuation from the summary and makes it lower case.
        except KeyError:
            entry['summary'] = ""
            nopunc_summary = ""
        test_whole_word = whole_word(nopunc_term)
        if test_whole_word(nopunc_title): #Checks if the word is present as a whole word in the title.
            rank += 2
        if test_whole_word(nopunc_summary): #Checks if the word is present as a whole word in the summary.
            rank += 1
    return rank

#   \brief - Returns whether the an entry already in the outlet's list links to the same article as a new entry.

#   \param entries - The list of entries.
#   \param candidate - The new entry to be checked for a match with another entry.

#   \returns Whether the new entry has the same link as an entry already present in the list (boolean).

def unique_entry(entries,candidate):
    for entry in entries:
        if entry['link'] == candidate['link']:
            return False #Returns False if the candidate entry has the same link as an entry already present in the list.
    return True

#   \brief - Returns the ranking from an entry.

#   \param entry - The entry containing the ranking.

#   \returns - The ranking for the entry.

def return_ranking(entry):
    return entry['ranking']


#   \brief - Loops through the data dictionary containing the RSS data, checking if each individual entry matches any of the key terms in a supplied list.

#   Copies all matching entries to separate lists for each outlet within a separate dictionary. Counts the number of entries matched.

#   Entries are also ranked per outlet based on how many terms match them. 

#   \param terms - The list containing the key terms to be matched.
#   \param data - The data dictionary containing all the RSS data.

#   \returns matched_data - The separate dictionary containing separate lists for each outlet stored at the key, which is the outlet's name, which have matched at least one of the terms.
#   \returns count - The number of entries matched.

def search_key_phrases(terms, data):
    count = 0
    matched_data = {}
    for outlet in data:
        for feed in data[outlet]:
            for entry in feed: #Loop through all invidual entries.
                ranking = rank_entries(terms, entry) #Find ranking of the entry.
                if ranking != 0: #Check if the entry matches any of the key word.
                    entry['ranking'] = ranking #Add the ranking under the "ranking" key in the entry.
                    try:
                        matched_data[outlet]
                    except KeyError:
                        matched_data[outlet] = [] #Create list for an outlet using its name as a key if it doesn't already exist in the matched_data dictionary.
                    if (unique_entry(matched_data[outlet], entry)):
                        matched_data[outlet].append(entry) #Append the list for the entry's outlet with the entry if the entry is unique.
                        count += 1
        try:
            matched_data[outlet]
        except KeyError:
            break
        else:
            matched_data[outlet].sort(key=return_ranking, reverse=True)
            for entry in matched_data[outlet]:
                del entry['ranking'] #If there are returned entries for the outlet, sort entries in ascending order of ranking, and then remove the ranking once it is no longer needed.
    return matched_data, count

#   \brief - Returns the count from a word and word count pair.

#   \param elem - The list containing the word and word count.

#   \returns - The word count for the word.

def return_count(elem):
    return elem[1]

#   \brief - Creates a new list, into which the list of words and counts is read, but different-case instances of the same words are removed.

#   The most common instance of the word is used and the counts for the other instances added on to its count.

#   \param words - The 2D list containing words and counts.
#   \param ranked - True if the words are in a pair with a ranking, False if they are simply strings alone in a list.

#   \returns - The new list with all different-case instances merged as described above. 

def rm_diff_case_repeats(words,ranked=True):
    new_words = []
    i=0
    while i < len(words): #Loop through all words.
        x=i+1
        if ranked:
            new_words.append([words[i][0],words[i][1]]) #Copy each word into new_words.

        while x < len(words): #Check each word against every word after itself.
            if ranked:
                if words[i][0].lower() == words[x][0].lower():
                    new_words[i][1] += words[x][1]
                    words.pop(x) #If two words have the same spelling but different case, remove the less popular word from the words list and add its count onto the more popular word's count in the new_words list.
                x+=1
            else:
                if words[i].lower() == words[x].lower():
                    print(words[i])
                    words.pop(x)
                x+=1
        i+=1
    if ranked:
        new_words.sort(key=return_count,reverse=True) #Sort new_words in descending order of word count.
        return new_words
    else:
        return words

#   \brief - Constructs a list containing all words found in titles and descriptions, then sorts them in descending order of frequency alongside their frequency.

#   \param data - The data dictionary containing all the fetched SRSS data.
#   \param blacklist - The list containing all the blacklisted (too common in English) words.

#   \returns new_words - A 2D list - the list of words, paired with their frequency. 

def most_common_phrases(data, blacklist):
    all_words = []
    for outlet in data:
        for feed in data[outlet]:
            for entry in feed:
                add_words = re.sub(r'[^\w\s-]','',entry['title']).split()+re.sub(r'[^\w\s-]','',entry['summary']).split()
                add_words = rm_diff_case_repeats(add_words,False) #Remove repeated words from the list to be added.
                all_words += add_words #Reads all words found in titles and descriptions into a list, removing all punctuation marks. Repeats in a single story are not counted.
    words = (Counter(all_words).most_common()) #Gets words into a 2d list alongside their respective frequencies in all_words, as well as sorting them in decreasing order of frequency.
    i=0
    while i < len(words): #Remove all words which are in the blacklist from the list.
        for word in blacklist:
            if words[i][0].lower() == word.strip():
                words.pop(i)
                i -= 1
                break
        i += 1
    words = rm_diff_case_repeats(words)
    return words

#   \brief - Uses two dictionaries to create a two-way mapping between an issue name and a safe version of the name which can be used in a URL.

#   \param issue - The issue name.
#   \param safe_to_string - The dictionary which uses the safe version of the issue name as the key and the original issue name as the value.
#   \param string_to_safe - The dictionary which uses the original issue name as the key and the safe version of the issue name as the value.

def create_safe_mapping(issue,safe_to_string,string_to_safe):
    safe_issue = urllib.parse.quote_plus(issue)
    safe_to_string[safe_issue] = issue
    string_to_safe[issue] = safe_issue

#   \brief - Iterates through each issue in the issues dictionary and returns a dictionary containing the stories (within another dictionary under their outlets as keys) which match their tags and the number of stories for each issue.

#   Also creates two dictionaries comprising a two-way mapping between each issue name and a safe version of the name which can be used in a URL.

#   \param issues - The dictionary of tracked issues - each list of tags under the issue name as their key.
#   \param data - The data dictionary containing all the RSS data. 

#   \returns issues_data - The dictionary containing the stories and number of stories for each issue.
#   \returns safe_to_string - The dictionary which uses the safe version of the issue name as the key and the original issue name as the value.
#   \returns string_to_safe - The dictionary which uses the original issue name as the key and the safe version of the issue name as the value.


def get_issues(issues,data):
    issues_data = {}
    safe_to_string = {}
    string_to_safe = {}
    for issue in issues:
        create_safe_mapping(issue,safe_to_string,string_to_safe)
        count = 0
        matched_data, count = search_key_phrases(issues[issue],data) #Find the articles with titles or descriptions matching the issue tags.
        issues_data[issue] = {}
        issues_data[issue]['data'] = matched_data
        issues_data[issue]['count'] = count
    return issues_data, safe_to_string, string_to_safe

#   \brief - Splits the search term into an array of its different words before finding matching stories from the RSS data.

#   \param term - The search term entered by the user.
#   \param data - The data dictionary containing the RSS data.

#   \returns matched_data - The separate dictionary containing separate lists for each outlet stored at the key which is the outlet's name which have matched at least one of the terms.
#   \returns count - The number of entries matched.

def search(term, data):
    terms = term.split()
    return search_key_phrases(terms, data)

#   \brief - Loads the top issues and tracked issues data.

#   \param data - The data dictionary containing the RSS data.

def load():
    session['messages'] = read_json(messages_path,False)
    session['blacklist'] = read_blacklist(blacklist_path)
    session['issues'] = read_json(issues_json_path)
    session['default_issues'] = read_json(default_issues_json_path)
    session['active_default_issues'] = get_active_defaults(session['default_issues'])
    session['issues_data'], session['safe_to_string'], session['string_to_safe'] = get_issues({**session.get('issues'),**session.get('active_default_issues')},session.get('feeds'))
    common_words = most_common_phrases(session.get('feeds'),session.get('blacklist'))
    del common_words[10:]
    session['common_words'] = common_words

#   \brief - Loads the RSS data from the most recent archive and generates the top issues and tracked issues data from that.

def basic_load():
    session['feeds_list'] = read_json(feeds_json_path) #Reads the feeds in from the supplied JSON file into a dictionary under the outlet as the key.
    session['default_feeds_list'] = read_json(default_feeds_json_path)
    session['active_default_feeds'] = get_active_defaults(session['default_feeds_list'])
    session['feeds'] = read_default_archive(archive_path)
    load()

#   \brief - Refreshes the RSS data, top issues and data found for tracked issues from the tracked RSS feeds.

def refresh():
    session['feeds_list'] = read_json(feeds_json_path) #Reads the feeds in from the supplied JSON file into a dictionary under the outlet as the key.
    session['default_feeds_list'] = read_json(default_feeds_json_path)
    session['active_default_feeds'] = get_active_defaults(session['default_feeds_list'])
    session['feeds'] = get_feeds()
    load()


#Render the homepage.
@main_bp.route("/")
def home():
    #Redirect user to dashboard if they are logged in
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))
    return render_template('home.html')

#Render the dashboard.
@main_bp.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    alerts = read_json(alerts_path,False) #Read alerts from alerts file.
    for alert in alerts:
        flash(alert)
    write_json([],alerts_path) #Wipe all alerts once they have been displayed.
    if request.method == 'POST':
        if request.form['refresh'] == 'Refresh feeds':
            refresh() #Refresh the page if the user clicks on the "Refresh feeds" button.
    return render_template('dashboard.html', current_user = current_user.name, issues_data = session['issues_data'], common_words = session['common_words'], string_to_safe = session['string_to_safe'])

#Render a page full of stories for each issue.
@main_bp.route("/issue/<issue_name>")
@login_required
def get_issue(issue_name):
    issues_data = session.get('issues_data')
    safe_to_string = session.get('safe_to_string')
    return render_template('view_issue.html', issue_data = issues_data[safe_to_string[issue_name]], issue = safe_to_string[issue_name])

#Renders a search bar if the page is loaded directly or the search bar is empty, but otherwise loads search results.
@main_bp.route("/search", methods=['GET', 'POST'])
@login_required
def search_tags():
    if request.method == 'GET':
        try:
            word = request.args['word']
        except KeyError:
            return (render_template('search_get.html', current_user = current_user.name))
        search_data, count = search(word,session.get('feeds'))
        return (render_template('view_search.html', current_user = current_user.name, search_query = word, search_data = search_data, count=count))
    search_tags_str = request.form.get('search')
    if search_tags_str == "":
        return (render_template('search_get.html', current_user = current_user.name))
    search_data, count = search(search_tags_str,session.get('feeds'))
    return (render_template('view_search.html', current_user = current_user.name, search_query = search_tags_str, search_data = search_data, count=count))

#Creates a redirect to /search with word as the search term.

@main_bp.route("/search_word/<word>")
@login_required
def redirect_search(word):
    return redirect(url_for('main_bp.search_tags', word=word, current_user = current_user.name))

#Creates an interface to add, remove and edit tracked issues and their tags and tracked outlets and their feeds.
@main_bp.route("/track/<target>", methods=['GET', 'POST'])
@login_required
def track_target(target):
    if target == "issues":
        separator = ","
        page = "track_issues.html"
        container = session.get('issues')
        default_container = session.get('default_issues')
        active_default_container = session.get('active_default_issues')
        json_path = issues_json_path
        default_json_path = default_issues_json_path
    elif target == "outlets":
        separator = "\r\n"
        page = "track_outlets.html"
        container = session.get('feeds_list')
        default_container = session.get('default_feeds_list')
        active_default_container = session.get('active_default_feeds')
        json_path = feeds_json_path
        default_json_path = default_feeds_json_path #Set variables depending on whether issues or outlets are being managed.
    if request.method == 'POST':
        try:
            added_key = request.form['add_key']
            added_vals = request.form['add_vals'] #Check if the form for adding keys has been submitted.
        except KeyError:
            try:
                removed_key = request.form['rm_key'] #Check if the form for removing keys has been submitted.
            except KeyError:
                try:
                    edited_key = request.form['edit_key']
                    new_vals = request.form['edit_vals'] #Check if the form for editing keys has been submitted.
                except KeyError:
                    try:
                        new_defaults = request.form.getlist('change_defaults')
                    except KeyError:
                        pass
                    else:
                        for key in default_container:
                            default_container[key][1] = False
                        for key in new_defaults:
                            default_container[key][1] = True
                        write_json(default_container,default_json_path)
                        active_default_container = get_active_defaults(default_container)
                        if target == "issues":
                            session['default_issues'] = default_container
                            session['active_default_issues'] = get_active_defaults(default_container)
                            message = "Changed default tracked issues."
                        else:
                            session['default_feeds_list'] = default_container
                            session['active_default_list'] = get_active_defaults(default_container)
                            message = "Changed default tracked outlets."
                else:
                    if edited_key == "" or new_vals == "":
                        if target == "issues":
                            message = "No issue selected or new tags empty!"
                        else:
                            message = "No outlet selected or new feeds empty!" #Set the message to warn the user if no key is selected.
                    add_val(container,edited_key,new_vals.split(separator))
                    write_json(container,json_path)
                    if target == "issues":
                        message = "Edited issue: "+edited_key+" - "+new_vals+"."
                    else:
                        message = "Edited outlet: "+edited_key+"." #Edit the key's tags to the relevant dictionary and save the changes to file. Set the message to say which key has been added, referring to whether the user is managing issues or outlets.
                    
            else:
                if removed_key == "":
                    if target == "issues":
                        message = "No issue selected."
                    else:
                        message = "No outlet selected."  #Set the message to warn the user if no key is selected.
                else:
                    rm_val(container,removed_key)
                    write_json(container,json_path)
                    if target == "issues":
                        message = "Removed issue: "+removed_key+"."
                    else:
                        message = "Removed outlet: "+removed_key+"." #Remove keys from relevant dictionary and save the changes to file. Set the message to say which key has been removed, referring to whether the user is managing issues or outlets.
        else:
            if added_key == "" or added_vals == "":
                if target == "issues":
                    message = "Missing issue name or tags." #Set the message to warn the user if the key name or values are missing.
                else:
                    message = "Missing outlet name or feeds."
            elif added_key in list(container.keys()):
                if target == "issues":
                    message = "Issue name is the same as another issue." #Set the message to warn the user if the key name is the same as another in the container.
                else:
                    message = "Outlet name is the same as another outlet."
            elif any(not (c.isalnum() or c=="-" or c==" ") for c in added_key):
                if target == "issues":
                    message = "Issue names can only contains alphanumeric characters, spaces and hyphens." #Set the message to warn the user if they attempt to add an issue with a name which is not entirely alphanumeric (excepting spaces and hyphens, which are known to work.
                else:
                    message = "Outlet names can only contains alphanumeric characters, spaces and hyphens."
            else:
                add_val(container,added_key,added_vals.split(separator))
                write_json(container,json_path)
                if target == "issues":
                    message = "Added issue: "+added_key+" - "+added_vals+"."
                else:
                    message = "Added outlet: "+added_key+"." #Add keys and values to relevant dictionary and save the changes to file. Set the message to say which issue has been added, referring to whether the user is managing issues or outlets.
    try:
        message
    except NameError:
        return (render_template(page, current_user = current_user.name, data=container, default_data=default_container, active_default_data=active_default_container))
    else:
        return (render_template(page, current_user = current_user.name, data=container, default_data=default_container, active_default_data=active_default_container, message=message))

#Creates an interface to request support and read support messages.
@main_bp.route("/support", methods=['GET','POST'])
@login_required
def support_messaging():
    if request.method == "POST":
        new_message = request.form['send_msg']
        if new_message != "":
            ts = datetime.now()
            session['messages'].insert(0,{"sender":current_user.name,"date":ts.strftime("%B %d, %Y at %H:%M:%S"), "message":new_message})
            write_json(session['messages'],messages_path)
            #Write message to all the JSON file containing all the support messages sent by users.
            all_messages = read_json(all_messages_path,False,False)
            all_messages.insert(0,{"sender":current_user.name,"date":ts.strftime("%B %d, %Y at %H:%M:%S"), "message":new_message})
            write_json(all_messages,all_messages_path,False)
    return (render_template('support_messaging.html', current_user = current_user.name, messages=session['messages']))

#Creates an interface to change preferences, such as changing the username and password.
@main_bp.route("/preferences", methods=['GET','POST'])
@login_required
def preferences():
    if request.method == 'POST':
        if request.form['type'] == "change_pass":
            change_form = ChangePasswordForm(request.form)
            if change_form.validate():
                old_password = request.form.get('old_password')
                new_password = request.form.get('new_password')
                if current_user.check_password(password=old_password):
                    current_user.password = generate_password_hash(new_password, method='sha256')
                    db.session.add(current_user)
                    db.session.commit()
                    flash('Password successfully changed.')
                else:
                    flash('Current password incorrect.')
            else:
                flash_form_errors(change_form) #Flash validation errors if validation fails.
        else:
            change_form = ChangeUsernameForm(request.form)
            if change_form.validate():
                password = request.form.get('password')
                new_name = request.form.get('new_name')
                if current_user.check_password(password=password):
                    existing_user = User.query.filter_by(name=new_name).first()
                    if existing_user == None:
                        current_user.name = new_name
                        db.session.add(current_user)
                        db.session.commit()
                        flash('Username succesfully changed.')
                    else:
                        flash('A user already exists with that username.')
                else:
                    flash('Password incorrect.')
            else:
                flash_form_errors(change_form) #Flash validation errors if validation fails.
    return (render_template('preferences.html', current_user = current_user.name))
