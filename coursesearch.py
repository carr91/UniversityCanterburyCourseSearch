import requests
from bs4 import BeautifulSoup
import csv
import re

search_terms = [
    "Cognitive", "generative", "large language model", "Cyber", "genAI", "llm",
    "deep learning", "Artificial Intelligence", "artificial intelligence",
    "Neural Network", "Deep Learning", "AI Ethics", "Machine Learning",
    "Computer Vision", "Natural Language Processing", "Reinforcement Learning",
    "AI Safety", "Generative Models", "Artificial General Intelligence"
]

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
    headers = {"User-Agent": "Mozilla/5.0"}

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
    seen = set()
    unique_courses = []
    for course in course_data:
        essential_fields = (course[0])
        if essential_fields not in seen:
            seen.add(essential_fields)
            unique_courses.append(course)
    return unique_courses

def sort_courses_by_code(course_data):
    def extract_number(course_code):
        match = re.search(r'(\d+)', course_code)
        return int(match.group(1)) if match else float('inf')

    return sorted(course_data, key=lambda row: extract_number(row[0]))

def combine_courses_by_title_and_info(course_data):
    combined_courses = {}
    for course in course_data:
        title = course[1]
        if title in combined_courses:
            combined_courses[title][0] += f"/{course[0]}"
            combined_courses[title][4] += f"/{course[4]}"
        else:
            combined_courses[title] = course[:]
    return list(combined_courses.values())

def fetch_course_details(keyword):
    url = f"https://courseinfo.canterbury.ac.nz/GetCourseDetails.aspx?course={keyword.replace(' ', '%20')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        return soup
    else:
        print(f"Failed to retrieve details for {keyword}, status code: {response.status_code}")
        return None

def parse_course_details(soup):
    restrictions = []
    equivalents = []
    prerequisites = []
    contact_person = []
    base_url = "https://courseinfo.canterbury.ac.nz/"

    restrictions_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl00_PCRDescriptionLabel")
    if restrictions_section:
        restrictions = [link.text for link in restrictions_section.find_all("a")]

    equivalents_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl01_PCRDescriptionLabel")
    if equivalents_section:
        equivalents = [link.text for link in equivalents_section.find_all("a")]

    prerequisites_section = soup.find("span", id="ctl00_ContentPlaceHolder1_PCRRepeater_ctl00_PCRDescriptionLabel")
    if prerequisites_section:
        prerequisites_text = prerequisites_section.get_text(separator=" ").strip()
        prerequisites_links = [link.text for link in prerequisites_section.find_all("a")]
        prerequisites = [prerequisites_text] + prerequisites_links

    contact_person_section = soup.find("div", id="ctl00_ContentPlaceHolder1_ContributorsDiv")
    if contact_person_section:
        contact_person_link = contact_person_section.find("a")
        if contact_person_link and 'href' in contact_person_link.attrs:
            href = contact_person_link['href']
            if href.startswith("ShowPeopleDetails.aspx"):
                href = base_url + href
            contact_person.append(f"{contact_person_link.text} ({href})")

    return restrictions, equivalents, prerequisites, contact_person

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
            writer.writerow([course[0], course[1], course[3], course[4]])

    print_to_interface(f"Results saved to {output_file}, now parsing detailed info...")

    with open(output_file, "r", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    header.extend(["Restrictions", "Equivalents", "Prerequisites", "Contact Person", "Mapping to Graduate Attributes"])
    header = [
        "Course Code",
        "Course URL",
        "Course Title",
        "Credits",
        "Other Info",
        "Restrictions",
        "Equivalents",
        "Prerequisites",
        "Contact Person",
        "Mapping to Graduate Attributes"
    ]


    final_data = []
    for row in data:
        course_codes = row[0].split("/")
        restrictions = set()
        equivalents = set()
        prerequisites = set()
        contact_persons = set()

        for course_code in course_codes:
            soup = fetch_course_details(course_code.strip())
            print_to_interface(f"Finding Contacts, Restrictions, Equivalents, and prerequisites for {course_code.strip()}...")
            if soup:
                course_restrictions, course_equivalents, course_prerequisites, course_contact_person = parse_course_details(soup)
                restrictions.update(course_restrictions)
                equivalents.update(course_equivalents)
                prerequisites.update(course_prerequisites)
                contact_persons.update(course_contact_person)

        row.extend([
            ", ".join(restrictions),
            ", ".join(equivalents),
            ", ".join(prerequisites),
            ", ".join(contact_persons),
            " "
        ])

        detail_url = f"https://courseinfo.canterbury.ac.nz/GetCourseDetails.aspx?course={course_codes[0].strip().replace(' ', '%20')}"
        final_row = [
            row[0],              # Course Code
            detail_url,          # Course URL
            row[1],              # Course Title
            row[2],              # Credits
            row[3],              # Other Info
            row[4],              # Restrictions
            row[5],              # Equivalents
            row[6],              # Prerequisites
            row[7],              # Contact Person
            row[8],              # Mapping to Graduate Attributes
        ]

        final_data.append(final_row)

    with open(output_file, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(final_data)

    print_to_interface(f"Final updated course info saved to {output_file}")
