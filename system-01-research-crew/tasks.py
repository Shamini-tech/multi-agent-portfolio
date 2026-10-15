from crewai import Task
from agents import searcher, analyst, writer

search_task = Task(
    description="Search the web for recent and credible sources on the topic: {topic}",
    expected_output="A list of 5-8 sources with titles, URLs, and 1-line relevance notes.",
    agent=searcher
)

analyze_task = Task(
    description="Analyze the gathered sources and extract the 3-5 strongest claims with concrete evidence.",
    expected_output="A structured breakdown of key claims, supporting evidence, and source attribution.",
    agent=analyst
)

write_task = Task(
    description="Synthesize the analyzed claims into a clean, concise technical report tailored for busy engineers.",
    expected_output="A final structured report containing a 2-sentence summary, 3-5 headed sections, and a complete source list.",
    agent=writer
)