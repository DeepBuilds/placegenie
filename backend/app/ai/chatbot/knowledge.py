"""The built-in placement guide.

A small, curated set of general guidance topics (not hundreds of canned replies). A student's question
is matched to the closest topics with TF-IDF cosine similarity. The same topics are given to an LLM as
reference notes when one is configured, so both paths give consistent advice.

Nothing here is specific to a real company, and nothing claims to know a hiring decision or schedule:
that information does not exist in PlaceGenie.
"""
from dataclasses import dataclass, field
from functools import lru_cache

from app.ai.text_similarity import tfidf_similarities

MIN_MATCH = 0.12  # below this similarity the question is considered outside the guide


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    keywords: str  # words and phrases students use when asking about this topic
    answer: str  # plain text; "- " bullets
    follow_ups: tuple[str, ...] = field(default_factory=tuple)


TOPICS: tuple[Topic, ...] = (
    Topic(
        "about", "What PlaceGenie AI can help with",
        "what can you do help features about placegenie assistant how does this work what are you",
        "I can help you with placement preparation and with your own PlaceGenie data:\n"
        "- Check whether you are eligible for a job and explain why or why not\n"
        "- Suggest jobs that match your profile, and show your skill gaps\n"
        "- Show your applications and upcoming interviews\n"
        "- Review your resume analysis and suggest improvements\n"
        "- Give general guidance on interviews, aptitude tests, resumes, projects and job roles\n"
        "I give guidance only. I do not know any company's hiring decisions or schedules, and the placement cell has the final word.",
        ("Which jobs am I eligible for?", "How should I prepare for placements?"),
    ),
    Topic(
        "process", "Typical campus placement process",
        "placement process stages rounds how does campus placement work steps procedure selection process drive",
        "Rounds differ from company to company, but a campus drive usually looks like this:\n"
        "- Eligibility: the company sets criteria such as CGPA, branch and backlogs\n"
        "- Registration or application through the placement cell, before the deadline\n"
        "- Pre-placement talk or briefing about the company and role\n"
        "- Online test (aptitude, reasoning, sometimes coding)\n"
        "- Group discussion for some companies\n"
        "- Technical interview(s), then an HR interview\n"
        "- Offer, usually communicated through the placement cell\n"
        "Check each job's own details in PlaceGenie, because the actual rounds are decided by the company.",
        ("How do I prepare for an aptitude test?", "How do I prepare for a technical interview?"),
    ),
    Topic(
        "prep_plan", "Placement preparation plan",
        "how to prepare for placements preparation plan roadmap timeline where to start strategy study plan",
        "A simple plan you can adapt:\n"
        "- Start early: build a weekly routine instead of cramming before drives\n"
        "- Aptitude: practise a little every day (quant, logical reasoning, verbal)\n"
        "- Coding: solve problems regularly in one language you know well, focusing on arrays, strings, hashing and basic recursion\n"
        "- Core subjects: revise DBMS and SQL, OOP, operating systems and networks\n"
        "- Projects: be ready to explain 2 or 3 of them in depth\n"
        "- Resume: keep it to one page and update it after every project or certificate\n"
        "- Mock interviews: practise answering aloud with a friend\n"
        "Use the Skill gap and Recommended pages to see what to focus on for the jobs you want.",
        ("What should my resume include?", "How do I prepare for the HR interview?"),
    ),
    Topic(
        "aptitude", "Aptitude test preparation",
        "aptitude test quantitative reasoning logical verbal online assessment preparation practice mcq numerical",
        "Most online assessments start with aptitude questions.\n"
        "- Quantitative: percentages, ratios, time and work, speed and distance, averages, probability basics\n"
        "- Logical reasoning: series, puzzles, seating arrangements, data interpretation\n"
        "- Verbal: grammar, reading comprehension, sentence correction\n"
        "- Practise with a timer, because speed matters as much as accuracy\n"
        "- Learn shortcuts for common calculations, and review every mistake\n"
        "- Take full-length timed mock tests in the last weeks",
        ("How do I prepare for coding rounds?",),
    ),
    Topic(
        "coding", "Coding and data structures practice",
        "coding practice dsa data structures algorithms leetcode problems programming round competitive coding test",
        "For coding rounds and technical interviews:\n"
        "- Pick one language and know it well, including its standard library\n"
        "- Cover the basics first: arrays, strings, hash maps, stacks and queues, linked lists, sorting and searching, recursion\n"
        "- Then trees, graphs, and simple dynamic programming\n"
        "- Solve problems on a regular schedule; after each one, note the pattern you used\n"
        "- Practise writing code without an editor's help, and explain your approach aloud\n"
        "- Always mention time and space complexity",
        ("What core subjects should I revise?",),
    ),
    Topic(
        "cs_core", "Core computer science subjects",
        "core subjects dbms os operating system computer networks oop sql revise fundamentals computer science subjects",
        "Interviewers often ask these fundamentals:\n"
        "- DBMS and SQL: normalisation, keys, joins, indexes, transactions, writing queries\n"
        "- OOP: classes, inheritance, polymorphism, encapsulation, abstraction\n"
        "- Operating systems: processes and threads, scheduling, memory management, deadlocks\n"
        "- Computer networks: OSI/TCP-IP layers, HTTP, DNS, TCP vs UDP\n"
        "- Your own language: how it handles memory, errors and common data structures\n"
        "Revise with small examples you can explain in your own words.",
        ("How do I prepare for a technical interview?",),
    ),
    Topic(
        "technical_interview", "Technical interview tips",
        "technical interview preparation tips questions how to crack technical round prepare interview technical",
        "To do well in a technical interview:\n"
        "- Revise your resume: anything on it can be asked, especially projects and listed skills\n"
        "- Think aloud: explain your approach before you write code\n"
        "- Ask a clarifying question if the problem is unclear\n"
        "- Start with a simple solution, then improve it\n"
        "- If you do not know something, say so honestly and explain how you would find out\n"
        "- Test your solution with a small example\n"
        "Be ready to explain the design choices and challenges in your projects.",
        ("How should I present my projects?", "How do I prepare for the HR interview?"),
    ),
    Topic(
        "hr_interview", "HR interview tips",
        "hr interview questions tell me about yourself strengths weaknesses why should we hire you behavioural star method",
        "Common HR questions and how to approach them:\n"
        "- Tell me about yourself: 3 or 4 sentences covering education, key skills or projects, and what you want next\n"
        "- Strengths and weaknesses: be honest, give an example, and show what you are doing to improve\n"
        "- Why this company or role: read about the company and connect it to your interests\n"
        "- Behavioural questions: use the STAR method (Situation, Task, Action, Result)\n"
        "- Be ready to discuss gaps, backlogs or a low score honestly and positively\n"
        "Practise aloud, keep answers short, and ask one or two thoughtful questions at the end.",
        ("What if I have a low CGPA?",),
    ),
    Topic(
        "gd", "Group discussion tips",
        "group discussion gd tips topics how to speak initiate conclude participation",
        "In a group discussion the panel looks at communication, listening and teamwork:\n"
        "- Listen first and understand the topic before speaking\n"
        "- Make short, structured points; support them with a fact or example\n"
        "- Build on others' points and disagree politely\n"
        "- Do not dominate or interrupt, but do contribute regularly\n"
        "- If you can, summarise the discussion at the end\n"
        "Practise by discussing current topics with friends.",
        (),
    ),
    Topic(
        "resume_writing", "Writing a good fresher resume",
        "resume writing tips improve resume cv format what to include how to write resume fresher one page structure",
        "A strong fresher resume:\n"
        "- One page, clean layout, easy-to-read font, saved as a PDF\n"
        "- Sections: contact details, education (with CGPA), skills, projects, internships or experience, certifications\n"
        "- Start each bullet with an action verb (Built, Designed, Analysed) and quantify results where you honestly can\n"
        "- Name the technologies used in every project\n"
        "- List only skills you can discuss in an interview\n"
        "- Add your LinkedIn and GitHub links, and proofread for spelling\n"
        "Upload your resume in PlaceGenie to get a section-by-section review.",
        ("How can I make my resume match a job?", "How should I present my projects?"),
    ),
    Topic(
        "resume_keywords", "Matching your resume to a job",
        "ats keywords resume match job description tailor resume shortlisting screening filter keywords",
        "Many companies screen resumes by skills and keywords before a person reads them.\n"
        "- Read the job's required skills and make sure the ones you truly have appear on your resume\n"
        "- Use the same names the job uses (for example SQL, Python, REST APIs)\n"
        "- Show each skill in context, such as a project where you used it\n"
        "- Do not list skills you cannot back up: you may be asked about them\n"
        "The Skill gap page shows which of a job's skills your profile has and which you are missing.",
        ("Show my skill gap",),
    ),
    Topic(
        "projects", "Presenting your projects",
        "projects how to present explain my project project ideas good projects college project github portfolio",
        "Interviewers use projects to judge how you work.\n"
        "- Prepare a 1 minute summary: the problem, your solution, the technologies, your role\n"
        "- Know the details: why you chose those tools, what went wrong, what you would improve\n"
        "- Highlight what you personally built if it was a team project\n"
        "- Put the code on GitHub with a clear README, and add results or screenshots\n"
        "- A small project you understand fully beats a large one you cannot explain",
        ("How do I prepare for a technical interview?",),
    ),
    Topic(
        "low_cgpa", "Low CGPA or backlogs",
        "low cgpa backlogs arrears low marks not eligible poor grades less percentage backlog problem",
        "Eligibility criteria such as minimum CGPA and the number of backlogs are set by each company, so some jobs may be closed to you.\n"
        "- Check which open jobs you are eligible for in PlaceGenie: some have lower or no CGPA limits\n"
        "- Clear backlogs as early as you can, since many companies allow none\n"
        "- Strengthen what you can control: skills, projects, internships and certifications\n"
        "- Be ready to explain your academic record honestly and positively in interviews\n"
        "I cannot promise that any company will make an exception.",
        ("Which jobs am I eligible for?", "Show my skill gap"),
    ),
    Topic(
        "internships", "Internships",
        "internship intern how to get internship summer training experience stipend first experience",
        "Internships give real experience and often help with full-time hiring.\n"
        "- Look for internships in PlaceGenie by filtering jobs by type\n"
        "- Build a few projects first so you have something to show\n"
        "- Apply early and keep your resume and GitHub up to date\n"
        "- Add completed internships to your profile's Experience section and to your resume, with what you actually did",
        (),
    ),
    Topic(
        "online_presence", "LinkedIn and GitHub",
        "linkedin github profile portfolio online presence networking professional profile",
        "A tidy online presence helps recruiters learn more about you.\n"
        "- LinkedIn: a clear photo, headline, summary, education, skills and projects\n"
        "- GitHub: pin your best projects, write READMEs, commit regularly\n"
        "- Keep contact details consistent with your resume\n"
        "- Make sure nothing public hurts your image",
        (),
    ),
    Topic(
        "role_data_analyst", "Data Analyst role",
        "data analyst role skills what does a data analyst do prepare data analyst sql excel power bi tableau statistics",
        "Data analysts turn data into insights and reports.\n"
        "- Core skills: SQL, Excel, a BI tool such as Power BI or Tableau, and basic statistics\n"
        "- Helpful: Python with pandas, clear communication, data visualisation\n"
        "- Prepare: SQL queries (joins, grouping, window functions), explaining a dashboard you built, interpreting a small dataset\n"
        "- Projects that help: a dashboard on a public dataset, a data-cleaning and analysis notebook",
        ("Show my skill gap",),
    ),
    Topic(
        "role_software", "Software Engineer, backend, frontend and full-stack roles",
        "software engineer developer backend frontend full stack web developer role skills java python javascript react node prepare",
        "Software roles build and maintain applications.\n"
        "- Everyone: data structures and algorithms, OOP, Git, SQL basics, problem solving\n"
        "- Backend: a server language (Java, Python, Node.js), REST APIs, databases\n"
        "- Frontend: HTML, CSS, JavaScript, and a framework such as React\n"
        "- Full-stack: a mix of both, plus how they connect\n"
        "- Prepare: coding problems, a project you can explain end to end, and basics of how the web and databases work",
        ("How do I prepare for coding rounds?",),
    ),
    Topic(
        "role_ml", "Data Scientist and Machine Learning roles",
        "data scientist machine learning engineer ml ai role skills python statistics scikit learn deep learning prepare",
        "These roles build models from data.\n"
        "- Core skills: Python, statistics and probability, pandas and NumPy, machine learning basics (scikit-learn)\n"
        "- Helpful: SQL, data visualisation, deep learning frameworks, model evaluation\n"
        "- Prepare: explain how common algorithms work, how to evaluate a model, and how you cleaned and used data in a project\n"
        "- Projects that help: an end-to-end project from raw data to a evaluated model",
        ("Show my skill gap",),
    ),
    Topic(
        "role_devops", "DevOps and Cloud roles",
        "devops cloud engineer aws azure docker kubernetes linux ci cd role skills infrastructure prepare",
        "These roles deploy and run software reliably.\n"
        "- Core skills: Linux, Git, networking basics, a cloud platform (AWS, Azure or Google Cloud), Docker\n"
        "- Helpful: CI/CD pipelines, Kubernetes, scripting in Python or Bash\n"
        "- Prepare: explain how you would deploy an application, basic Linux commands, and what containers are\n"
        "- Projects that help: containerise an app and deploy it with an automated pipeline",
        ("Show my skill gap",),
    ),
    Topic(
        "role_qa", "QA and Software Testing roles",
        "qa tester testing software testing quality assurance selenium test cases manual automation role skills",
        "QA engineers make sure software works as intended.\n"
        "- Core skills: testing concepts, writing test cases, bug reporting, SQL basics\n"
        "- Helpful: automation (for example Selenium), a scripting language, API testing\n"
        "- Prepare: test case design, types of testing, and how you would test a common feature such as a login page",
        (),
    ),
    Topic(
        "role_security", "Cyber Security roles",
        "cyber security analyst security role network security linux ethical hacking skills prepare certification",
        "Security analysts protect systems and respond to threats.\n"
        "- Core skills: networking, Linux, security fundamentals (authentication, encryption, common attacks)\n"
        "- Helpful: scripting, security tools, an entry-level certification if the job asks for one\n"
        "- Prepare: explain common attacks and defences, the CIA triad, and how you would investigate a suspicious event",
        (),
    ),
    Topic(
        "role_core", "Core engineering and embedded roles",
        "core engineering mechanical electrical civil electronics embedded graduate engineer trainee autocad matlab role skills",
        "Core engineering roles use your branch's fundamentals.\n"
        "- Revise your core subjects thoroughly; interviews are usually subject-based\n"
        "- Learn the tools your branch uses (for example AutoCAD, MATLAB, embedded C, circuit simulation)\n"
        "- Be ready to talk about a project, internship or plant visit\n"
        "- Many core companies run aptitude and technical tests like IT companies do",
        (),
    ),
    Topic(
        "role_business", "Business Analyst role",
        "business analyst role requirements gathering excel sql communication skills prepare analyst trainee",
        "Business analysts connect business needs with technical teams.\n"
        "- Core skills: communication, Excel, SQL basics, structured problem solving\n"
        "- Helpful: a BI tool, documentation, understanding of how a business works\n"
        "- Prepare: practise explaining a problem and your solution clearly, and a simple case question",
        (),
    ),
    Topic(
        "soft_skills", "Communication and soft skills",
        "communication skills soft skills confidence english speaking body language teamwork nervous anxiety fear interview",
        "Soft skills often decide close calls.\n"
        "- Practise speaking out loud: record yourself or practise with friends\n"
        "- Keep answers clear and structured, and listen to the whole question first\n"
        "- Maintain eye contact (or look at the camera in online interviews) and sit upright\n"
        "- Nervousness is normal: slow down, breathe, and it is fine to pause and think\n"
        "- Show curiosity and honesty",
        (),
    ),
    Topic(
        "interview_day", "Interview day checklist",
        "interview day checklist what to carry dress code online interview setup tips before interview documents punctual",
        "Before an interview:\n"
        "- Confirm the date, time, venue or meeting link in advance\n"
        "- Carry printed resumes and your ID and certificates; dress neatly\n"
        "- For an online round, test your internet, camera, microphone and a quiet space beforehand\n"
        "- Join a few minutes early\n"
        "- Revise your resume, projects and the company's role\n"
        "- Note your questions and afterwards record the interview in PlaceGenie's tracker",
        ("Show my upcoming interviews",),
    ),
    Topic(
        "how_eligibility", "How eligibility works in PlaceGenie",
        "how does eligibility work eligibility criteria rules cgpa branch backlogs checked explained why eligible not eligible",
        "PlaceGenie compares your profile with a job's requirements using fixed rules:\n"
        "- CGPA at least the job's minimum\n"
        "- Your branch is allowed\n"
        "- Backlogs within the limit\n"
        "- All required skills present in your profile\n"
        "- Required certifications held, and enough experience if asked\n"
        "- The application deadline has not passed\n"
        "If something is missing from your profile it says so rather than guessing. It is guidance: the company and placement cell decide.",
        ("Which jobs am I eligible for?",),
    ),
    Topic(
        "how_recommendations", "How recommendations and skill gaps work",
        "how are jobs recommended how recommendation works match score percentage skill gap explained priority calculated",
        "Recommendations are scored out of 100 from the parts of your profile you have filled in:\n"
        "- Skill match (largest part), CGPA fit, preferred roles, interests and projects, and your resume\n"
        "- Jobs you are not eligible for are reduced in score but still shown, with reasons\n"
        "The skill gap page lists a job's skills you have and those you lack, ordered by how essential they are and how often open jobs ask for them. "
        "Each card explains its own score.",
        ("Recommend jobs for me",),
    ),
    Topic(
        "learn_skill", "How to learn a new skill",
        "how to learn a skill learn new technology start learning study resources roadmap beginner practice course free",
        "A practical way to learn a skill you are missing:\n"
        "- Start with the official documentation or a well-reviewed beginner course\n"
        "- Build something small with it straight away; projects make the skill stick\n"
        "- Practise a little every day instead of long gaps\n"
        "- Write what you learned in your own words, and add the skill to your resume only when you can discuss it\n"
        "I cannot tell you how long it will take, because that depends on you and your background.",
        ("Show my skill gap",),
    ),
    Topic(
        "realtime_limits", "What the assistant cannot know",
        "will i get selected hiring decision result announced company visiting dates shortlisted chances of selection when will results come offer",
        "I do not have real-time information about companies. I cannot tell you whether a company will select you, whether a result has been announced, or when a company will visit.\n"
        "- The status of your applications in PlaceGenie is whatever the placement cell has recorded: see My applications\n"
        "- For company schedules, results and offers, check with the placement cell or the company's official communication",
        ("Show my applications",),
    ),
)

TOPICS_BY_ID = {t.id: t for t in TOPICS}


@dataclass(frozen=True)
class Match:
    topic: Topic
    score: float


def _corpus() -> list[str]:
    return [f"{t.title} {t.keywords} {t.keywords} {t.answer}" for t in TOPICS]


@lru_cache(maxsize=1)
def _topic_texts() -> tuple[str, ...]:
    return tuple(_corpus())


def search(question: str, limit: int = 3) -> list[Match]:
    """The topics closest to the question, best first (only those above MIN_MATCH)."""
    if not question.strip():
        return []
    sims = tfidf_similarities([question], list(_topic_texts()))[0]
    ranked = sorted(zip(sims, TOPICS), key=lambda p: -p[0])
    return [Match(t, round(s, 4)) for s, t in ranked[:limit] if s >= MIN_MATCH]


def best_answer(question: str) -> tuple[str, tuple[str, ...]] | None:
    """The guide's reply to a question, or None if no topic is close enough.

    If a role guide and a general topic both match well (for example "prepare for a data analyst
    interview"), both are shown.
    """
    matches = search(question, limit=2)
    if not matches:
        return None
    first = matches[0]
    text, follow_ups = first.topic.answer, first.topic.follow_ups
    if len(matches) == 2 and matches[1].score >= 0.6 * first.score:
        second = matches[1].topic
        text = f"{text}\n\nAlso relevant: {second.title}\n{second.answer}"
        follow_ups = tuple(dict.fromkeys([*follow_ups, *second.follow_ups]))[:3]
    return text, follow_ups
