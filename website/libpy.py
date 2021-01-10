from flask.helpers import url_for
import requests
import uvicorn
import shutil
import os
import re
from threading import Thread
from urllib.parse import unquote
from bs4 import BeautifulSoup
from flask import Flask, render_template, session,request,Response
from uuid import uuid4

from werkzeug.utils import redirect

app = Flask(__name__)
app.secret_key = 'abc'
s = requests.Session()

LIB_LINK = 'http://1.186.28.31/MIT/Question%20Paper.aspx'
getDetails = lambda soup: {'__EVENTVALIDATION': soup.select('#__EVENTVALIDATION')[0]['value'],'__VIEWSTATEGENERATOR': soup.select('#__VIEWSTATEGENERATOR')[0]['value'],'__VIEWSTATE': soup.select('#__VIEWSTATE')[0]['value']}
getList = lambda container: [i.text.replace('\xa0','') for i in container]
getNList = lambda soup: soup.find_all('a',{'id': re.compile('ctl00_ctl00_chmain_MITContent_FileGridCS_gvFiles')})[1:]
getURL = lambda soup: ['http://1.186.28.31/RootFolder/'+i['href'][3:] for i in soup.find_all('a',{'href': re.compile('.pdf',re.IGNORECASE)})[3:]]

BRANCHES = {
    'AEO':'Aeronautical.+',
    'ACH':'Architecture.+',
    'AUM':'Automobile.+',
    'BME':'Biomedical.+',
    'BTE':'Biotechnology.+',
    'CHM':'Chemical.+',
    'CVL':'Civil.+',
    'CCE':'Computer and Communication.+',
    'CSE':'Computer Science.+',
    'EEE':'Electrical and Electronics.+',
    'ECE':'Electronics and Communication.+',
    'FD':'Fashion.+',
    'IP':'Industrial.+',
    'IT': 'Information.+',
    'ICE':'Instrumentation.+',
    'ID':'Interior.+',
    'MME':'Mechanical+.',
    'MCT':'Mechatronics.+',
    'PNP':'Printing and Media.+'
}

def year_func(i,year,soup,BRANCH,SEM,DIRECTORY):
    # Retrieval of Batch Data(Odd/Even)
    data = getDetails(soup)
    data.update({'__EVENTTARGET':i})
    soup2 = BeautifulSoup(s.post(LIB_LINK,data=data).text,'html.parser')
    nav_list = getNList(soup2)
    data = getDetails(soup2)
    nav_list = [i['id'].replace('_','$') for i in nav_list]
    for i in nav_list:
        thread_func(i,data,year,BRANCH,SEM,DIRECTORY)

def thread_func(i,data,year,BRANCH,SEM,DIRECTORY):
    # Retrieval of Sems
    data.update({'__EVENTTARGET':i})
    soup3 = BeautifulSoup(s.post(LIB_LINK,data=data).text,'html.parser')
    data = getDetails(soup3)
    try:
        # Finding if Semester exists
        ID = soup3.find(text=re.compile('^\\s{}$'.format(SEM))).parent['id'].replace('_','$')
        data.update({'__EVENTTARGET':ID})
        soup4 = BeautifulSoup(s.post(LIB_LINK,data=data).text,'html.parser')
        URLs = list()
        # Finding if Branch exists
        if ((SEM != 'I Sem')&(SEM != 'II Sem')):
            ID = soup4.find(text=re.compile(BRANCHES[BRANCH])).parent['id'].replace('_','$')
            data = getDetails(soup4)
            data.update({'__EVENTTARGET':ID})
            soup5 = BeautifulSoup(s.post(LIB_LINK,data=data).text,'html.parser')
            URLs = getURL(soup5)
        else:
            URLs = getURL(soup4)
        with requests.Session() as s2:
            if not os.path.isdir(DIRECTORY + str(year)):
                os.makedirs(os.path.join(DIRECTORY,str(year)))
            for j in URLs:
                r = s2.get(j,verify=False,stream=True)
                name = os.path.join(DIRECTORY,str(year),unquote(j.split('/')[-1]))
                print(name)
                with open(name,"wb") as f:
                    f.write(r.content)
                f.close()
    except Exception:
        pass

@app.route('/')
def index():
    if 'directory' not in session:
        session['directory'] = uuid4()
    soup = BeautifulSoup(s.get(LIB_LINK).text,'html.parser')
    # Retrieving Year Data
    sem = ['I Sem','II Sem','III Sem','IV Sem','V Sem','VI Sem','VII Sem','VIII Sem','M.Tech','ICAS']	
    nav_years = getNList(soup)
    years = getList(nav_years)
    branch = BRANCHES.keys()
    return render_template('index.html',year = years,branch = branch,sem = sem)

@app.route('/submit',methods = ['POST'])
def submit():
    data = request.form
    L_YEAR = data['from']
    U_YEAR = data['to']
    BRANCH = data['branch']
    SEM = data['sem']
    DIRECTORY = os.path.join(app.instance_path,str(session['directory']),BRANCH,SEM)
    soup = BeautifulSoup(s.get(LIB_LINK).text,'html.parser')
    # Retrieving Year Data
    nav_years = getNList(soup)
    years = getList(nav_years)
    nav_years = [i['id'].replace('_','$') for i in nav_years[years.index(L_YEAR):years.index(U_YEAR)+1]]
    years = years[years.index(L_YEAR):years.index(U_YEAR)+1]
    t1 = []
    # Thread to navigate each year
    for i,y in enumerate(nav_years):
        t1.append(Thread(target=year_func,args=(y,int(years[i]),soup,BRANCH,SEM,DIRECTORY)))
    for i in t1:
        i.start()
    for i in t1:
        i.join()
    return render_template('submit.html')

@app.route('/download',methods = ['GET'])
def download():
    name = str(session['directory'])
    filename = os.path.join(app.instance_path,name)
    shutil.make_archive(filename,'zip',filename)
    shutil.rmtree(filename)
    file_path = filename + '.zip'
    print(name)
    with open(file_path,'rb') as f:
        data = f.readlines()
    os.remove(file_path)
    redirect(url_for('index'))
    return Response(data, headers={
        'Content-Type': 'application/zip',
        'Content-Disposition': 'attachment; filename=%s.zip;'%name})

if __name__ == '__main__':
    app.run()