import requests
from bs4 import BeautifulSoup
import csv
import re

search_terms = ["Cognitive", "generative", "large language model","Cyber","genAI", "llm", "deep learning", "Artificial Intelligence", "artificial intelligence", "Neural Network", "Deep Learning", "AI Ethics", "Machine Learning", "Computer Vision", "Natural Language Processing", "Reinforcement Learning", "AI Safety", "Generative Models", "Artificial General Intelligence"]


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_credits(course_name):
    match = re.search(r'(\d+ points)', course_name)
    if match:
        credits = match.group(1)
        course_name = course_name.replace(credits, '').strip()
    else:
        credits = ""
    return course_name, credits

def fetch_course_info(keyword, output_file):
    url = f"https://courseinfo.canterbury.ac.nz/GetCourses.aspx?Keyword={keyword.replace(' ', '%20')}&site=C"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    course_data = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="GetCourses")
        
        if table:
            rows = table.find_all("tr")
            previous_row = None
            
            for row in rows:
                cols = [clean_text(col.text) for col in row.find_all("td")]
                
                if len(cols) == 2 and cols[0] == "":
                    if previous_row:
                        previous_row[4] = cols[1]
                        course_data.append(previous_row)
                    continue
                
                elif len(cols) >= 2:
                    course_name, credits = extract_credits(cols[1])
                    cols[1] = course_name
                    
                    while len(cols) < 5:
                        cols.append("")
                    
                    cols[2] = keyword
                    cols[3] = credits
                    previous_row = cols
                    course_data.append(cols)
                    
        else:
            print(f"No course table found on the page for {keyword}.")
    else:
        print(f"Failed to retrieve page for {keyword}, status code: {response.status_code}")
    
    return course_data

def remove_duplicates(course_data):
    """Remove identical course entries from the dataset"""
    seen = set()
    unique_courses = []
    for course in course_data:
        print(course)
        course_tuple = tuple(course)
        if course_tuple not in seen:
            seen.add(course_tuple)
            unique_courses.append(course)
    return unique_courses

def sort_courses_by_code(course_data):
    """Sort courses by numerical portion of course code (fixed)"""
    def extract_number(course_code):
        match = re.search(r'(\d+)', course_code)
        return int(match.group(1)) if match else float('inf')
    
    return sorted(course_data, key=lambda row: extract_number(row[0]))

if __name__ == "__main__":
    output_file = "course_info.csv"
    
    with open(output_file, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Course Code", "Course Title", "Description", "Credits", "Other Info"])
    
    all_courses = []
    
    for term in search_terms:
        courses = fetch_course_info(term, output_file)
        all_courses.extend(courses)
    
    # New deduplication step
    unique_courses = remove_duplicates(all_courses)
    
    # Fixed sorting logic
    sorted_courses = sort_courses_by_code(unique_courses)
    
    with open(output_file, "a", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        for course in sorted_courses:
            writer.writerow(course)
    
    print(f"Results saved to {output_file}")
