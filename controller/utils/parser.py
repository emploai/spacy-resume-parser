import os
import multiprocessing as mp
import io
import re
import spacy
import pprint
from spacy.matcher import Matcher
from . import utils

nlp = spacy.load('en_core_web_sm')
custom_nlp = spacy.load('./models/resume_entity_parser')

class ResumeParser(object):
  def __init__(self, resume, skills_file=None, custom_regex=None):
    self.__skills_file = skills_file
    self.__custom_regex = custom_regex
    self.__matcher = Matcher(nlp.vocab)
    self.__details = {
      'basics': {},
      'work': [],
      'education': [],
      'skills': [],
      'summary': [],
    }

    self.__resume = resume
    if not isinstance(self.__resume, io.BytesIO):
      ext = os.path.splitext(self.__resume)[1].split('.')[1]
    else:
      ext = self.__resume.name.split('.')[1]
      
    self.__text_raw = utils.extract_text(self.__resume, '.' + ext)
    self.__text_split = [line.replace('\t', ' ') for line in self.__text_raw.split('\n') if line]
    self.__text_join = ' '.join(self.__text_split)
    self.__text = ' '.join(self.__text_join.split())
    self.__nlp = nlp(self.__text)
    self.__custom_nlp = custom_nlp(self.__text_join)
    self.__noun_chunks = list(self.__nlp.noun_chunks)
    self.__get_basic_details()

  def get_extracted_data(self):
    return self.__details

  def __get_basic_details(self):
    cust_ent = utils.extract_entities_wih_custom_model(self.__custom_nlp)
    name = utils.extract_name(self.__nlp, matcher=self.__matcher)
    email = utils.extract_email(self.__text)
    mobile = utils.extract_mobile(self.__text, self.__custom_regex)
    skills = utils.extract_skills(self.__nlp, self.__noun_chunks, self.__skills_file)

    # Extracting Sections From the Document
    sections = utils.extract_entity_sections(self.__text_raw)

    ''' EXTRACTING ALL DETAILS '''
    # ---------------------------------------------------------------------------
    # Extract Name
    try:
      self.__details['basics']['name'] = cust_ent['Name'][0]
    except (IndexError, KeyError):
      self.__details['basics']['name'] = name

    # ---------------------------------------------------------------------------
    # Extract Designation
    try:
      self.__details['basics']['label'] = cust_ent['Designation'][0]
    except (KeyError, IndexError) as e:
      pass

    # ---------------------------------------------------------------------------
    # Extract Email
    self.__details['basics']['email'] = email

    # ---------------------------------------------------------------------------
    # Extract Mobile Number
    self.__details['basics']['mobile'] = mobile

    # ---------------------------------------------------------------------------
    # Extract Skills
    if len(skills) > 0:
      for skill in skills: 
        self.__details['skills'].append({'name': skill})

    # ---------------------------------------------------------------------------
    # Extract Education
    education = {}
    institute = False
    try:
      if 'academic' in sections:
        sections['education'] = sections.pop('academic')  
      for element in sections['education']:
        temp = element.split()
        ent = utils.extract_entities_wih_spacy_model(nlp(element))
        if 'ORG' in ent:
          institute = ent['ORG'][0]
          education[institute] = {}
          education[institute]['degree'] = ''
          education[institute]['location'] = ''
          education[institute]['startDate'] = ''
          education[institute]['endDate'] = ''
          education[institute]['GPA'] = ''
          education[institute]['summary'] = []
        try:
          education[institute]['summary'].append(element)
        except (KeyError, IndexError) as e:
          pass
      
      for key in education:
        try:
          for line in education[key]['summary']:
            # Getting GPA
            ent = utils.extract_entities_wih_spacy_model(nlp(line))
            if 'PERCENT' in ent:
              education[key]['GPA'] = ent['PERCENT'][0]
            # Getting Degree
            custom_ent = utils.extract_entities_wih_custom_model(custom_nlp(' '.join(education[key]['summary'])))
            if 'Degree' in custom_ent:
              education[key]['degree'] = custom_ent['Degree'][0]
            # Getting Location
            if 'GPE' in ent:
              education[key]['location'] = ent['GPE'][0]
          # Getting Start and End Date
          exp_ = []
          for line in education[key]['summary']:
            dates = re.search(r'(?P<fmonth>\w+.\d+)\s*(\D|to)\s*(?P<smonth>\w+.\d+|present)', line, re.I)
            if dates:
              exp_.append(dates.groups())
          for i in exp_:
            education[key]['startDate'] = i[0]
            education[key]['endDate'] = i[2]
        except (KeyError, IndexError) as e:
          pass

      edukeys = list(education.keys())
      if len(edukeys) > 0:
        i = 0
        while i < len(edukeys):
          self.__details['education'].append({})
          self.__details['education'][i]['institution'] = edukeys[i]
          self.__details['education'][i]['location'] = education[edukeys[i]]['location']
          self.__details['education'][i]['studyType'] = education[edukeys[i]]['degree']
          self.__details['education'][i]['startDate'] = education[edukeys[i]]['startDate']
          self.__details['education'][i]['endDate'] = education[edukeys[i]]['endDate']
          self.__details['education'][i]['gpa'] = education[edukeys[i]]['GPA']
          self.__details['education'][i]['summary'] = ', '.join(education[edukeys[i]]['summary'])
          i += 1
      else:
        # Extract University Name
        try:
          self.__details['education'][0]['institution'] = cust_ent['College Name'][0]
        except (KeyError, IndexError) as e:
          pass
        # Extract Degree Name
        try:
          self.__details['education'][0]['degree'] = cust_ent['Degree'][0]
        except (KeyError, IndexError) as e:
          pass  
    except (KeyError, IndexError) as e:
      # Extract University Namey
      try:
        self.__details['education'][0]['institution'] = cust_ent['College Name'][0]
      except (KeyError, IndexError) as e:
        pass
      # Extract Degree Name
      try:
        self.__details['education'][0]['degree'] = cust_ent['Degree'][0]
      except (KeyError, IndexError) as e:
        pass

    # ---------------------------------------------------------------------------
    # Extract Work
    work = {}
    company = False
    try:
      for element in sections['experience']:
        # print(company, element)
        temp = element.split()
        ent = utils.extract_entities_wih_spacy_model(nlp(element))
        if len(temp) < 5:
          if 'ORG' in ent:
            company = ent['ORG'][0]
            work[company] = {}
            work[company]['position'] = ''
            work[company]['location'] = ''
            work[company]['startDate'] = ''
            work[company]['endDate'] = ''
            work[company]['summary'] = []
            continue
        try:
          work[company]['summary'].append(element)
        except (KeyError, IndexError) as e:
          pass
      
      for key in work:
        try:
          # Getting Years of Experience
          exp = round(utils.get_yofexp(work[key]['summary']) / 12, 2)
          work[key]['time'] = exp
          #  Getting Location
          for line in work[key]['summary']:
            ent = utils.extract_entities_wih_spacy_model(nlp(line))
            if 'GPE' in ent:
              work[key]['location'] = ent['GPE'][0]
          # Getting Start and End Date
          exp_ = []
          for line in work[key]['summary']:
            dates = re.search(r'(?P<fmonth>\w+.\d+)\s*(\D|to)\s*(?P<smonth>\w+.\d+|present)', line, re.I)
            if dates:
              exp_.append(dates.groups())
          for i in exp_:
            work[key]['startDate'] = i[0]
            work[key]['endDate'] = i[2]
          # Getting Position
          custom_ent = utils.extract_entities_wih_custom_model(custom_nlp(' '.join(work[key]['summary'])))
          if ('Designation') in custom_ent:
            work[key]['position'] = custom_ent['Designation'][0]
        except (KeyError, IndexError) as e:
          pass
      
      workkeys = list(work.keys())
      if len(workkeys) > 0:
        i = 0
        while i < len(workkeys):
          self.__details['work'].append({})
          self.__details['work'][i]['company'] = workkeys[i]
          self.__details['work'][i]['position'] = work[workkeys[i]]['position']
          self.__details['work'][i]['location'] = work[workkeys[i]]['location']
          self.__details['work'][i]['startDate'] = work[workkeys[i]]['startDate']
          self.__details['work'][i]['endDate'] = work[workkeys[i]]['endDate']
          self.__details['work'][i]['summary'] = ', '.join(work[workkeys[i]]['summary'])
          i += 1
      else: 
        # Extract Company Names
        try:
          if len(cust_ent['Companies worked at']) > 0:
            for company in cust_ent['Companies worked at']:
              self.__details['work'].append({'company': company})
        except (KeyError, IndexError) as e:
          pass

        # Extract Years of Experience 
        try:
          self.__details['summary'] = sections['summary']
          try:
            exp = round(utils.get_yofexp(sections['experience']) / 12, 2)
            self.__details['yofexp'] = exp
          except (KeyError, IndexError) as e:
            self.__details['yofexp'] = 0
        except (KeyError, IndexError) as e:
          self.__details['yofexp'] = 0
        self.__details['numpages'] = utils.get_number_of_pages(self.__resume)
    except (KeyError, IndexError) as e:
      # Extract Company Names
        try:
          if len(cust_ent['Companies worked at']) > 0:
            for company in cust_ent['Companies worked at']:
              self.__details['work'].append({'company': company})
        except (KeyError, IndexError) as e:
          pass

        # Extract Years of Experience 
        try:
          self.__details['summary'] = sections['summary']
          try:
            exp = round(utils.get_yofexp(sections['experience']) / 12, 2)
            self.__details['yofexp'] = exp
          except (KeyError, IndexError) as e:
            self.__details['yofexp'] = 0
        except (KeyError, IndexError) as e:
          self.__details['yofexp'] = 0
        self.__details['numpages'] = utils.get_number_of_pages(self.__resume)

    return


def resume_result_wrapper(resume):
  parser = ResumeParser(resume)
  return parser.get_extracted_data()


if __name__ == '__main__':
  pool = mp.Pool(mp.cpu_count())

  resumes = []
  data = []
  for root, directories, filenames in os.walk('resumes'):
    for filename in filenames:
      file = os.path.join(root, filename)
      resumes.append(file)

  results = [
    pool.apply_async(resume_result_wrapper, args=(x,)) for x in resumes
  ]

  results = [p.get() for p in results]

  pprint.pprint(results)
