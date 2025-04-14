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

def fetch_course_info(keyword, output_file, print_to_interface):
    print_to_interface(f"Fetching course information for keyword: {keyword}")
    url = f"https://courseinfo.canterbury.ac.nz/GetCourses.aspx?Keyword={keyword.replace(' ', '%20')}&site=C"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    course_data = []

    if response.status_code == 200:
        print_to_interface(f"Successfully retrieved data for keyword: {keyword}")
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="GetCourses")
        
        if table:
            print_to_interface(f"Parsing course table for keyword: {keyword}")
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
            print_to_interface(f"No course table found for keyword: {keyword}")
    else:
        print_to_interface(f"Failed to retrieve page for keyword: {keyword}, status code: {response.status_code}")
    
    return course_data

def remove_duplicates(course_data):
    """Remove duplicate course entries based on essential fields."""
    seen = set()
    unique_courses = []
    for course in course_data:
        # Create a tuple of only the essential fields for comparison
        essential_fields = (course[0])  # Exclude the search term (course[2])
        if essential_fields not in seen:
            seen.add(essential_fields)
            unique_courses.append(course)
        
    return unique_courses

def sort_courses_by_code(course_data):
    """Sort courses by numerical portion of course code (fixed)"""
    def extract_number(course_code):
        match = re.search(r'(\d+)', course_code)
        return int(match.group(1)) if match else float('inf')
    
    return sorted(course_data, key=lambda row: extract_number(row[0]))

def combine_courses_by_title_and_info(course_data):
    """Combine course codes and 'Other Info' for entries with the same title."""
    combined_courses = {}
    
    for course in course_data:
        title = course[1]  # Use the Course Title as the key
        if title in combined_courses:
            # Combine course codes and 'Other Info' with a "/"
            combined_courses[title][0] += f"/{course[0]}"
            combined_courses[title][4] += f"/{course[4]}"
        else:
            # Add the course to the dictionary
            combined_courses[title] = course[:]
    
    # Return the combined courses as a list
    return list(combined_courses.values())

def fetch_course_details(keyword):
    """Fetch detailed course information for a specific course code."""
    url = f"https://courseinfo.canterbury.ac.nz/GetCourseDetails.aspx?course={keyword.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        return soup  # Return the parsed HTML content
    else:
        print(f"Failed to retrieve details for {keyword}, status code: {response.status_code}")
        return None

def parse_course_details(soup):
    """Parse restrictions, equivalent courses, prerequisites, and contact person (with hyperlink) from the course details page."""
    restrictions = []
    equivalents = []
    prerequisites = []
    contact_person = []

    # Base URL for contact person links
    base_url = "https://courseinfo.canterbury.ac.nz/"

    # Find the Restrictions section
    restrictions_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl00_PCRDescriptionLabel")
    if restrictions_section:
        restrictions = [link.text for link in restrictions_section.find_all("a")]

    # Find the Equivalent Courses section
    equivalents_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl01_PCRDescriptionLabel")
    if equivalents_section:
        equivalents = [link.text for link in equivalents_section.find_all("a")]

    # Find the Prerequisites section
    prerequisites_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl00_PCRDescriptionLabel")
    if prerequisites_section:
        # Extract text and links for prerequisites
        prerequisites_text = prerequisites_section.get_text(separator=" ").strip()
        prerequisites_links = [link.text for link in prerequisites_section.find_all("a")]
        prerequisites = [prerequisites_text] + prerequisites_links

    # Find the Contact Person section
    contact_person_section = soup.find("div", id="ctl00_ContentPlaceHolder1_ContributorsDiv")
    if contact_person_section:
        contact_person_link = contact_person_section.find("a")
        if contact_person_link and 'href' in contact_person_link.attrs:
            href = contact_person_link['href']
            # Prepend base URL if the link is relative
            if href.startswith("ShowPeopleDetails.aspx"):
                href = base_url + href
            contact_person.append(f"{contact_person_link.text} ({href})")

    return restrictions, equivalents, prerequisites, contact_person

def process_course_info(input_file, output_file):
    """Process course_info.csv to add Restrictions, Equivalents, Prerequisites, and Contact Person."""
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8", newline="") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Read the header and add new columns
        header = next(reader)
        header.extend(["Restrictions", "Equivalents", "Prerequisites", "Contact Person"])
        writer.writerow(header)
        
        for row in reader:
            course_codes = row[0].split("/")  # Split course codes if there are multiple
            restrictions = set()
            equivalents = set()
            prerequisites = set()
            contact_persons = set()
            
            for course_code in course_codes:
                soup = fetch_course_details(course_code.strip())
                if soup:
                    course_restrictions, course_equivalents, course_prerequisites, course_contact_person = parse_course_details(soup)
                    restrictions.update(course_restrictions)
                    equivalents.update(course_equivalents)
                    prerequisites.update(course_prerequisites)
                    contact_persons.update(course_contact_person)
            
            # Add the new data to the row
            row.extend([
                ", ".join(restrictions),  # Combine restrictions into a single string
                ", ".join(equivalents),   # Combine equivalents into a single string
                ", ".join(prerequisites), # Combine prerequisites into a single string
                ", ".join(contact_persons)  # Combine contact persons into a single string
            ])
            writer.writerow(row)

def rearrange_columns(input_file, output_file):
    """Move the 'Contact Person' column to be the second column in the CSV."""
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8", newline="") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # Read the header and rearrange columns
        header = next(reader)
        # Move "Contact Person" to the second position
        new_header = [header[0], header[7]] + header[1:7] + header[8:]
        writer.writerow(new_header)
        
        # Rearrange the rows
        for row in reader:
            new_row = [row[0], row[7]] + row[1:7] + row[8:]
            writer.writerow(new_row)

def main(keywords, print_to_interface):
    output_file = "course_info_final.csv"
    
    print_to_interface("Starting the course search process...")
    with open(output_file, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Course Code", "Course Title", "Credits", "Other Info"])
    
    all_courses = []
    
    for term in keywords:
        print_to_interface(f"Searching for courses with keyword: {term}")
        courses = fetch_course_info(term, output_file, print_to_interface)
        all_courses.extend(courses)
    
    print_to_interface("Deduplicating courses...")
    unique_courses = remove_duplicates(all_courses)
    
    print_to_interface("Combining courses with the same title...")
    combined_courses = combine_courses_by_title_and_info(unique_courses)
    
    print_to_interface("Sorting courses...")
    sorted_courses = sort_courses_by_code(combined_courses)
    
    with open(output_file, "a", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        for course in sorted_courses:
            writer.writerow([course[0], course[1], course[3], course[4]])  # Exclude course[2] (Description)
    
    print_to_interface(f"Results from search saved to {output_file}, Parsing each course for lecturers and requirements now...")

    # Process and rearrange the final CSV
    with open(output_file, "r", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Add new columns and process each course
    header.extend(["Restrictions", "Equivalents", "Prerequisites", "Contact Person"])
    header = [header[0], header[-1]] + header[1:-1]  # Move "Contact Person" to the second column

    final_data = []
    for row in data:
        course_codes = row[0].split("/")  # Split course codes if there are multiple
        restrictions = set()
        equivalents = set()
        prerequisites = set()
        contact_persons = set()
        
        for course_code in course_codes:
            soup = fetch_course_details(course_code.strip())
            print_to_interface(f"Finding Contacts, Restrictions,Equvialents,and prereqs for {course_code.strip()}...")
            if soup:
                course_restrictions, course_equivalents, course_prerequisites, course_contact_person = parse_course_details(soup)
                restrictions.update(course_restrictions)
                equivalents.update(course_equivalents)
                prerequisites.update(course_prerequisites)
                contact_persons.update(course_contact_person)

        # Add the new data to the row
        row.extend([
            ", ".join(restrictions),  # Combine restrictions into a single string
            ", ".join(equivalents),   # Combine equivalents into a single string
            ", ".join(prerequisites), # Combine prerequisites into a single string
            ", ".join(contact_persons)  # Combine contact persons into a single string
        ])
        # Rearrange the row to move "Contact Person" to the second position
        final_row = [row[0], row[-1]] + row[1:-1]
        final_data.append(final_row)

    # Write the final data to the same file
    with open(output_file, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(final_data)

    print_to_interface(f"Final updated course info saved to {output_file}")
