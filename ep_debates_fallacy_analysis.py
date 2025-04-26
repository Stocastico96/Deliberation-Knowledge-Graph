#!/usr/bin/env python3
"""
European Parliament Debates Fallacy Analysis

This script:
1. Converts European Parliament verbatim debates to Deliberation Knowledge Graph format
2. Analyzes speeches for logical fallacies using OpenRouter API
3. Stores the results in a structured format
"""

import os
import re
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from pydantic import BaseModel, Field, validator
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD

# LangChain
from langchain import PromptTemplate, LLMChain
from langchain_community.chat_models import ChatOpenAI

# ---------- 1) OpenRouter API Configuration ----------
# L'API key viene caricata dall'ambiente
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")
os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

# ---------- 2) Pydantic Models ----------
class Fallacy(BaseModel):
    type: str
    segment: str
    confidence: float

class Participant(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    affiliation: Optional[str] = None

class Contribution(BaseModel):
    id: str
    text: str
    timestamp: datetime
    participant_id: str
    topic_id: Optional[str] = None
    fallacies: List[Fallacy] = Field(default_factory=list)

class Topic(BaseModel):
    id: str
    name: str

class DeliberationProcess(BaseModel):
    id: str
    name: str
    start_date: datetime
    end_date: datetime
    topics: List[Topic] = Field(default_factory=list)
    participants: List[Participant] = Field(default_factory=list)
    contributions: List[Contribution] = Field(default_factory=list)

# ---------- 3) Database Manager ----------
class DatabaseManager:
    def __init__(self, db_path="deliberation_kg.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deliberation_processes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id TEXT PRIMARY KEY,
                    process_id TEXT,
                    name TEXT NOT NULL,
                    FOREIGN KEY (process_id) REFERENCES deliberation_processes (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id TEXT PRIMARY KEY,
                    process_id TEXT,
                    name TEXT NOT NULL,
                    role TEXT,
                    affiliation TEXT,
                    FOREIGN KEY (process_id) REFERENCES deliberation_processes (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contributions (
                    id TEXT PRIMARY KEY,
                    process_id TEXT,
                    participant_id TEXT,
                    topic_id TEXT,
                    text TEXT NOT NULL,
                    timestamp TEXT,
                    has_fallacies BOOLEAN,
                    FOREIGN KEY (process_id) REFERENCES deliberation_processes (id),
                    FOREIGN KEY (participant_id) REFERENCES participants (id),
                    FOREIGN KEY (topic_id) REFERENCES topics (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fallacies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contribution_id TEXT,
                    type TEXT,
                    segment TEXT,
                    confidence REAL,
                    FOREIGN KEY (contribution_id) REFERENCES contributions (id)
                )
            """)

    def store_deliberation_process(self, process: DeliberationProcess):
        """Store a complete deliberation process with all related entities."""
        with sqlite3.connect(self.db_path) as conn:
            # Store the process
            conn.execute(
                """
                INSERT OR REPLACE INTO deliberation_processes (id, name, start_date, end_date)
                VALUES (?, ?, ?, ?)
                """,
                (
                    process.id,
                    process.name,
                    process.start_date.isoformat(),
                    process.end_date.isoformat()
                )
            )
            
            # Store topics
            for topic in process.topics:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO topics (id, process_id, name)
                    VALUES (?, ?, ?)
                    """,
                    (topic.id, process.id, topic.name)
                )
            
            # Store participants
            for participant in process.participants:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO participants (id, process_id, name, role, affiliation)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        participant.id,
                        process.id,
                        participant.name,
                        participant.role,
                        participant.affiliation
                    )
                )
            
            # Store contributions and fallacies
            for contribution in process.contributions:
                has_fallacies = len(contribution.fallacies) > 0
                conn.execute(
                    """
                    INSERT OR REPLACE INTO contributions (id, process_id, participant_id, topic_id, text, timestamp, has_fallacies)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contribution.id,
                        process.id,
                        contribution.participant_id,
                        contribution.topic_id,
                        contribution.text,
                        contribution.timestamp.isoformat(),
                        has_fallacies
                    )
                )
                
                # Store fallacies
                for fallacy in contribution.fallacies:
                    conn.execute(
                        """
                        INSERT INTO fallacies (contribution_id, type, segment, confidence)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            contribution.id,
                            fallacy.type,
                            fallacy.segment,
                            fallacy.confidence
                        )
                    )

    def get_deliberation_process(self, process_id: str) -> Optional[DeliberationProcess]:
        """Retrieve a complete deliberation process with all related entities."""
        with sqlite3.connect(self.db_path) as conn:
            # Get process
            process_df = pd.read_sql_query(
                "SELECT * FROM deliberation_processes WHERE id = ?",
                conn,
                params=(process_id,)
            )
            
            if process_df.empty:
                return None
            
            # Get topics
            topics_df = pd.read_sql_query(
                "SELECT * FROM topics WHERE process_id = ?",
                conn,
                params=(process_id,)
            )
            
            # Get participants
            participants_df = pd.read_sql_query(
                "SELECT * FROM participants WHERE process_id = ?",
                conn,
                params=(process_id,)
            )
            
            # Get contributions
            contributions_df = pd.read_sql_query(
                "SELECT * FROM contributions WHERE process_id = ?",
                conn,
                params=(process_id,)
            )
            
            # Get fallacies
            fallacies_df = pd.read_sql_query(
                """
                SELECT * FROM fallacies
                WHERE contribution_id IN (
                    SELECT id FROM contributions WHERE process_id = ?
                )
                """,
                conn,
                params=(process_id,)
            )
            
            # Build topics
            topics = []
            for _, row in topics_df.iterrows():
                topics.append(Topic(
                    id=row["id"],
                    name=row["name"]
                ))
            
            # Build participants
            participants = []
            for _, row in participants_df.iterrows():
                participants.append(Participant(
                    id=row["id"],
                    name=row["name"],
                    role=row["role"],
                    affiliation=row["affiliation"]
                ))
            
            # Build contributions with fallacies
            contributions = []
            for _, row in contributions_df.iterrows():
                c_id = row["id"]
                
                # Get fallacies for this contribution
                fallacies = []
                for _, f_row in fallacies_df[fallacies_df["contribution_id"] == c_id].iterrows():
                    fallacies.append(Fallacy(
                        type=f_row["type"],
                        segment=f_row["segment"],
                        confidence=f_row["confidence"]
                    ))
                
                contributions.append(Contribution(
                    id=c_id,
                    text=row["text"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    participant_id=row["participant_id"],
                    topic_id=row["topic_id"],
                    fallacies=fallacies
                ))
            
            # Build the complete process
            process_row = process_df.iloc[0]
            return DeliberationProcess(
                id=process_row["id"],
                name=process_row["name"],
                start_date=datetime.fromisoformat(process_row["start_date"]),
                end_date=datetime.fromisoformat(process_row["end_date"]),
                topics=topics,
                participants=participants,
                contributions=contributions
            )

    def get_all_process_ids(self) -> List[str]:
        """Get all process IDs in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM deliberation_processes")
            return [row[0] for row in cursor.fetchall()]

    def get_fallacy_statistics(self, process_id: str) -> Dict[str, Any]:
        """Get statistics about fallacies in a deliberation process."""
        with sqlite3.connect(self.db_path) as conn:
            # Total contributions
            total_contributions = conn.execute(
                "SELECT COUNT(*) FROM contributions WHERE process_id = ?",
                (process_id,)
            ).fetchone()[0]
            
            # Contributions with fallacies
            contributions_with_fallacies = conn.execute(
                "SELECT COUNT(*) FROM contributions WHERE process_id = ? AND has_fallacies = 1",
                (process_id,)
            ).fetchone()[0]
            
            # Fallacy types and counts
            fallacy_types_df = pd.read_sql_query(
                """
                SELECT type, COUNT(*) as count
                FROM fallacies
                WHERE contribution_id IN (
                    SELECT id FROM contributions WHERE process_id = ?
                )
                GROUP BY type
                ORDER BY count DESC
                """,
                conn,
                params=(process_id,)
            )
            
            # Participants with most fallacies
            participants_fallacies_df = pd.read_sql_query(
                """
                SELECT p.name, COUNT(f.id) as fallacy_count
                FROM participants p
                JOIN contributions c ON p.id = c.participant_id
                JOIN fallacies f ON c.id = f.contribution_id
                WHERE p.process_id = ?
                GROUP BY p.id
                ORDER BY fallacy_count DESC
                LIMIT 10
                """,
                conn,
                params=(process_id,)
            )
            
            return {
                "total_contributions": total_contributions,
                "contributions_with_fallacies": contributions_with_fallacies,
                "percentage_with_fallacies": (contributions_with_fallacies / total_contributions * 100) if total_contributions > 0 else 0,
                "fallacy_types": fallacy_types_df.to_dict(orient="records") if not fallacy_types_df.empty else [],
                "participants_with_most_fallacies": participants_fallacies_df.to_dict(orient="records") if not participants_fallacies_df.empty else []
            }

# ---------- 4) HTML Parser for European Parliament Debates ----------
class EPDebateParser:
    def parse_html(self, html_content: str) -> DeliberationProcess:
        """Parse European Parliament debate HTML into a DeliberationProcess object."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract debate metadata
        date_str = self._extract_date(soup)
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Create the deliberation process
        process_id = f"ep_debate_{date.strftime('%Y%m%d')}"
        process = DeliberationProcess(
            id=process_id,
            name=f"European Parliament Debate - {date_str}",
            start_date=datetime.combine(date, datetime.min.time()),
            end_date=datetime.combine(date, datetime.max.time()),
            topics=[],
            participants=[],
            contributions=[]
        )
        
        # Extract topics
        topics = self._extract_topics(soup)
        for i, topic_name in enumerate(topics, 1):
            topic_id = f"topic_{i}"
            process.topics.append(Topic(
                id=topic_id,
                name=topic_name
            ))
        
        # Extract speeches and speakers
        speeches = self._extract_speeches(soup)
        
        # Process speakers and their contributions
        participant_map = {}  # To avoid duplicates
        
        for i, speech in enumerate(speeches, 1):
            speaker_name = speech.get('speaker', 'Unknown')
            speaker_role = speech.get('role')
            speaker_affiliation = speech.get('affiliation')
            speech_text = speech.get('text', '')
            speech_time = speech.get('time')
            
            # Skip empty speeches
            if not speech_text.strip():
                continue
            
            # Create or get participant
            participant_id = f"participant_{speaker_name.replace(' ', '_')}"
            if participant_id not in participant_map:
                participant = Participant(
                    id=participant_id,
                    name=speaker_name,
                    role=speaker_role,
                    affiliation=speaker_affiliation
                )
                process.participants.append(participant)
                participant_map[participant_id] = participant
            
            # Create contribution
            contribution_id = f"contribution_{i}"
            
            # Parse timestamp
            timestamp = None
            if speech_time:
                try:
                    time_obj = datetime.strptime(speech_time, "%H:%M:%S").time()
                    timestamp = datetime.combine(date, time_obj)
                except ValueError:
                    timestamp = datetime.combine(date, datetime.min.time())
            else:
                timestamp = datetime.combine(date, datetime.min.time())
            
            # Find relevant topic
            topic_id = None
            if len(process.topics) > 0:
                topic_id = process.topics[0].id  # Default to first topic
            
            contribution = Contribution(
                id=contribution_id,
                text=speech_text,
                timestamp=timestamp,
                participant_id=participant_id,
                topic_id=topic_id
            )
            
            process.contributions.append(contribution)
        
        return process
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract the debate date from the HTML."""
        # This is a placeholder - actual implementation would depend on HTML structure
        date_elem = soup.find('div', class_='date')
        if date_elem:
            date_text = date_elem.text.strip()
            # Extract date in YYYY-MM-DD format
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
            if date_match:
                return date_match.group(1)
        
        # If date not found, use a default or current date
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_topics(self, soup: BeautifulSoup) -> List[str]:
        """Extract debate topics from the HTML."""
        topics = []
        
        # Look for table of contents or agenda items
        toc_elems = soup.find_all('h2', class_='title')
        for elem in toc_elems:
            topics.append(elem.text.strip())
        
        # If no topics found, add a default one
        if not topics:
            topics.append("General Debate")
        
        return topics
    
    def _extract_speeches(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract speeches and speaker information from the HTML."""
        speeches = []
        
        # Find speech containers
        speech_elems = soup.find_all('div', class_='speech')
        
        for elem in speech_elems:
            # Extract speaker info
            speaker_elem = elem.find('span', class_='speaker')
            speaker_name = speaker_elem.text.strip() if speaker_elem else "Unknown"
            
            # Extract role
            role_elem = elem.find('span', class_='role')
            role = role_elem.text.strip() if role_elem else None
            
            # Extract affiliation
            affiliation_elem = elem.find('span', class_='affiliation')
            affiliation = affiliation_elem.text.strip() if affiliation_elem else None
            
            # Extract speech text
            text_elem = elem.find('div', class_='text')
            text = text_elem.text.strip() if text_elem else ""
            
            # Extract time
            time_elem = elem.find('span', class_='time')
            time = time_elem.text.strip() if time_elem else None
            
            speeches.append({
                'speaker': speaker_name,
                'role': role,
                'affiliation': affiliation,
                'text': text,
                'time': time
            })
        
        return speeches

# ---------- 5) JSON-LD Converter ----------
class JsonLdConverter:
    def __init__(self):
        self.dkg = Namespace("https://w3id.org/deliberation/ontology#")
        self.base_uri = "https://w3id.org/deliberation/resource/"
    
    def process_to_jsonld(self, process: DeliberationProcess) -> Dict[str, Any]:
        """Convert a DeliberationProcess to JSON-LD format."""
        jsonld = {
            "@context": {
                "dkg": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#"
            },
            "@type": "dkg:DeliberationProcess",
            "dkg:identifier": process.id,
            "dkg:name": process.name,
            "dkg:startDate": process.start_date.isoformat(),
            "dkg:endDate": process.end_date.isoformat(),
            "dkg:hasTopic": [],
            "dkg:hasParticipant": [],
            "dkg:hasContribution": []
        }
        
        # Add topics
        for topic in process.topics:
            jsonld["dkg:hasTopic"].append({
                "@type": "dkg:Topic",
                "dkg:identifier": topic.id,
                "dkg:name": topic.name
            })
        
        # Add participants
        for participant in process.participants:
            p_json = {
                "@type": "dkg:Participant",
                "dkg:identifier": participant.id,
                "dkg:name": participant.name
            }
            
            if participant.role:
                p_json["dkg:hasRole"] = {
                    "@type": "dkg:Role",
                    "dkg:name": participant.role
                }
            
            if participant.affiliation:
                p_json["dkg:isAffiliatedWith"] = {
                    "@type": "dkg:Organization",
                    "dkg:name": participant.affiliation
                }
            
            jsonld["dkg:hasParticipant"].append(p_json)
        
        # Add contributions
        for contribution in process.contributions:
            c_json = {
                "@type": "dkg:Contribution",
                "dkg:identifier": contribution.id,
                "dkg:text": contribution.text,
                "dkg:timestamp": contribution.timestamp.isoformat(),
                "dkg:madeBy": {"@id": contribution.participant_id}
            }
            
            if contribution.topic_id:
                c_json["dkg:hasTopic"] = {"@id": contribution.topic_id}
            
            # Add fallacies if any
            if contribution.fallacies:
                c_json["dkg:hasFallacies"] = []
                for fallacy in contribution.fallacies:
                    c_json["dkg:hasFallacies"].append({
                        "@type": "dkg:Fallacy",
                        "dkg:type": fallacy.type,
                        "dkg:segment": fallacy.segment,
                        "dkg:confidence": fallacy.confidence
                    })
            
            jsonld["dkg:hasContribution"].append(c_json)
        
        return jsonld
    
    def jsonld_to_rdf(self, jsonld: Dict[str, Any]) -> Graph:
        """Convert JSON-LD to RDF graph."""
        g = Graph()
        
        # Define namespaces
        g.bind("dkg", self.dkg)
        g.bind("rdf", RDF)
        g.bind("rdfs", RDFS)
        g.bind("xsd", XSD)
        
        # Add deliberation process
        process_uri = URIRef(self.base_uri + jsonld["dkg:identifier"])
        g.add((process_uri, RDF.type, self.dkg.DeliberationProcess))
        g.add((process_uri, self.dkg.identifier, Literal(jsonld["dkg:identifier"])))
        g.add((process_uri, self.dkg.name, Literal(jsonld["dkg:name"])))
        
        if "dkg:startDate" in jsonld:
            g.add((process_uri, self.dkg.startDate, Literal(jsonld["dkg:startDate"], datatype=XSD.dateTime)))
        
        if "dkg:endDate" in jsonld:
            g.add((process_uri, self.dkg.endDate, Literal(jsonld["dkg:endDate"], datatype=XSD.dateTime)))
        
        # Add topics
        for topic in jsonld.get("dkg:hasTopic", []):
            topic_uri = URIRef(self.base_uri + topic["dkg:identifier"])
            g.add((topic_uri, RDF.type, self.dkg.Topic))
            g.add((topic_uri, self.dkg.identifier, Literal(topic["dkg:identifier"])))
            g.add((topic_uri, self.dkg.name, Literal(topic["dkg:name"])))
            
            # Link topic to process
            g.add((process_uri, self.dkg.hasTopic, topic_uri))
        
        # Add participants
        for participant in jsonld.get("dkg:hasParticipant", []):
            participant_uri = URIRef(self.base_uri + participant["dkg:identifier"])
            g.add((participant_uri, RDF.type, self.dkg.Participant))
            g.add((participant_uri, self.dkg.identifier, Literal(participant["dkg:identifier"])))
            g.add((participant_uri, self.dkg.name, Literal(participant["dkg:name"])))
            
            # Add role if available
            if "dkg:hasRole" in participant:
                role_uri = URIRef(self.base_uri + "role_" + participant["dkg:identifier"])
                g.add((role_uri, RDF.type, self.dkg.Role))
                g.add((role_uri, self.dkg.name, Literal(participant["dkg:hasRole"]["dkg:name"])))
                g.add((participant_uri, self.dkg.hasRole, role_uri))
            
            # Add affiliation if available
            if "dkg:isAffiliatedWith" in participant:
                org_name = participant["dkg:isAffiliatedWith"]["dkg:name"]
                org_uri = URIRef(self.base_uri + "org_" + org_name.replace("/", "_").replace(" ", "_"))
                g.add((org_uri, RDF.type, self.dkg.Organization))
                g.add((org_uri, self.dkg.name, Literal(org_name)))
                g.add((participant_uri, self.dkg.isAffiliatedWith, org_uri))
            
            # Link participant to process
            g.add((process_uri, self.dkg.hasParticipant, participant_uri))
        
        # Add contributions
        for contribution in jsonld.get("dkg:hasContribution", []):
            contribution_uri = URIRef(self.base_uri + contribution["dkg:identifier"])
            g.add((contribution_uri, RDF.type, self.dkg.Contribution))
            g.add((contribution_uri, self.dkg.identifier, Literal(contribution["dkg:identifier"])))
            g.add((contribution_uri, self.dkg.text, Literal(contribution["dkg:text"])))
            
            # Add timestamp if available
            if "dkg:timestamp" in contribution:
                g.add((contribution_uri, self.dkg.timestamp, Literal(contribution["dkg:timestamp"], datatype=XSD.dateTime)))
            
            # Link to participant
            if "dkg:madeBy" in contribution and "@id" in contribution["dkg:madeBy"]:
                participant_id = contribution["dkg:madeBy"]["@id"]
                participant_uri = URIRef(self.base_uri + participant_id)
                g.add((contribution_uri, self.dkg.madeBy, participant_uri))
            
            # Link to topic if available
            if "dkg:hasTopic" in contribution and "@id" in contribution["dkg:hasTopic"]:
                topic_id = contribution["dkg:hasTopic"]["@id"]
                topic_uri = URIRef(self.base_uri + topic_id)
                g.add((contribution_uri, self.dkg.hasTopic, topic_uri))
            
            # Add fallacies if any
            for fallacy in contribution.get("dkg:hasFallacies", []):
                fallacy_uri = URIRef(self.base_uri + "fallacy_" + contribution["dkg:identifier"] + "_" + fallacy["dkg:type"].replace(" ", "_"))
                g.add((fallacy_uri, RDF.type, self.dkg.Fallacy))
                g.add((fallacy_uri, self.dkg.type, Literal(fallacy["dkg:type"])))
                g.add((fallacy_uri, self.dkg.segment, Literal(fallacy["dkg:segment"])))
                g.add((fallacy_uri, self.dkg.confidence, Literal(fallacy["dkg:confidence"], datatype=XSD.float)))
                g.add((contribution_uri, self.dkg.hasFallacy, fallacy_uri))
            
            # Link contribution to process
            g.add((process_uri, self.dkg.hasContribution, contribution_uri))
        
        return g

# ---------- 6) Fallacy Detection Agent ----------
class FallacyDetectionAgent:
    def __init__(self, temperature: float = 0.0):
        self.llm = ChatOpenAI(
            model="deepseek/deepseek-r1-distill-llama-70b:free",
            temperature=temperature,
            max_tokens=1024,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=BASE_URL
        )

        self.system_instructions = (
            "You are an expert in logical fallacy detection. Your task is to analyze arguments "
            "and identify any logical fallacies present.\n\n"
            "For each fallacy found:\n"
            "1) type 2) exact text segment 3) confidence score (0-1)\n\n"
            "If no fallacies, return empty JSON array: []\n"
            "Respond ONLY with JSON in the following format:\n"
            "[\n"
            "  {\n"
            '    "type": "Ad Hominem",\n'
            '    "segment": "text snippet",\n'
            '    "confidence": 0.95\n'
            "  }\n"
            "]"
        )

        self.fallacy_prompt = PromptTemplate(
            input_variables=["system_instructions", "user_text"],
            template="{system_instructions}\n\nAnalyze the following text:\n{user_text}\n\nJSON response only:"
        )

        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.fallacy_prompt,
            verbose=False
        )

    def analyze_text(self, text: str) -> List[Fallacy]:
        if not text.strip():
            return []
        try:
            response = self.chain.run(
                system_instructions=self.system_instructions,
                user_text=text
            )
            print(f"Raw LLM Fallacy Detection Output: {response}")

            return self._parse_fallacies_json(response)
        except Exception as e:
            print(f"Error during fallacy analysis: {e}")
            return []

    def _parse_fallacies_json(self, llm_output: str) -> List[Fallacy]:
        llm_output = llm_output.strip().replace("```json", "").replace("```", "")
        match = re.search(r"(\[.*\])", llm_output, re.DOTALL)
        if match:
            raw_json = match.group(1)
            try:
                data = json.loads(raw_json)
                if isinstance(data, list):
                    result = []
                    for item in data:
                        try:
                            f = Fallacy(
                                type=item.get("type", ""),
                                segment=item.get("segment", ""),
                                confidence=float(item.get("confidence", 0.0))
                            )
                            result.append(f)
                        except Exception as e:
                            print(f"Parsing fallacy item error: {e}")
                    return result
            except json.JSONDecodeError:
                print("Unable to decode model's JSON response.")
        return []

# ---------- 7) Main Processing Pipeline ----------
class DebateProcessingPipeline:
    def __init__(self):
        self.db = DatabaseManager()
        self.parser = EPDebateParser()
        self.converter = JsonLdConverter()
        self.fallacy_detector = FallacyDetectionAgent(temperature=0.2)
    
    def process_html_file(self, html_file_path: str, analyze_fallacies: bool = True) -> str:
        """Process an HTML file containing European Parliament debate."""
        print(f"Processing HTML file: {html_file_path}")
        
        # Read HTML file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML to DeliberationProcess
        process = self.parser.parse_html(html_content)
        process_id = process.id
        
        # Analyze fallacies if requested
        if analyze_fallacies:
            print("Analyzing fallacies in contributions...")
            for contribution in process.contributions:
                print(f"Analyzing contribution {contribution.id}...")
                fallacies = self.fallacy_detector.analyze_text(contribution.text)
                contribution.fallacies = fallacies
                if fallacies:
                    print(f"Found {len(fallacies)} fallacies in contribution {contribution.id}")
                    for fallacy in fallacies:
                        print(f"  - {fallacy.type}: '{fallacy.segment}' (confidence: {fallacy.confidence})")
        
        # Store in database
        print("Storing process in database...")
        self.db.store_deliberation_process(process)
        
        # Convert to JSON-LD
        print("Converting to JSON-LD...")
        jsonld = self.converter.process_to_jsonld(process)
        
        # Convert to RDF
        print("Converting to RDF...")
        rdf_graph = self.converter.jsonld_to_rdf(jsonld)
        
        # Save JSON-LD to file
        jsonld_file = html_file_path.replace('.html', '.jsonld')
        with open(jsonld_file, 'w', encoding='utf-8') as f:
            json.dump(jsonld, f, indent=2)
        
        # Save RDF to file
        rdf_file = html_file_path.replace('.html', '.rdf')
        rdf_graph.serialize(destination=rdf_file, format="xml")
        
        print(f"Process completed. Files saved: {jsonld_file}, {rdf_file}")
        
        return process_id
    
    def generate_fallacy_report(self, process_id: str, output_file: str = None):
        """Generate a report of fallacies detected in a deliberation process."""
        print(f"Generating fallacy report for process: {process_id}")
        
        # Get process from database
        process = self.db.get_deliberation_process(process_id)
        if not process:
            print(f"Process not found: {process_id}")
            return
        
        # Get fallacy statistics
        stats = self.db.get_fallacy_statistics(process_id)
        
        # Generate report
        report = {
            "process_id": process_id,
            "process_name": process.name,
            "date": process.start_date.strftime("%Y-%m-%d"),
            "statistics": stats,
            "fallacies_by_contribution": []
        }
        
        # Add fallacies by contribution
        for contribution in process.contributions:
            if contribution.fallacies:
                participant = next((p for p in process.participants if p.id == contribution.participant_id), None)
                report["fallacies_by_contribution"].append({
                    "contribution_id": contribution.id,
                    "participant": participant.name if participant else "Unknown",
                    "text": contribution.text,
                    "fallacies": [
                        {
                            "type": f.type,
                            "segment": f.segment,
                            "confidence": f.confidence
                        }
                        for f in contribution.fallacies
                    ]
                })
        
        # Save report to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {output_file}")
        
        return report

# ---------- 8) Command-line interface ----------
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='European Parliament Debates Fallacy Analysis')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Process HTML file command
    process_parser = subparsers.add_parser('process', help='Process an HTML file')
    process_parser.add_argument('html_file', help='Path to the HTML file')
    process_parser.add_argument('--no-fallacies', action='store_true', help='Skip fallacy analysis')
    
    # Generate report command
    report_parser = subparsers.add_parser('report', help='Generate a fallacy report')
    report_parser.add_argument('process_id', help='Process ID')
    report_parser.add_argument('--output', help='Output file path')
    
    # List processes command
    list_parser = subparsers.add_parser('list', help='List all processes')
    
    args = parser.parse_args()
    
    pipeline = DebateProcessingPipeline()
    
    if args.command == 'process':
        pipeline.process_html_file(args.html_file, not args.no_fallacies)
    
    elif args.command == 'report':
        pipeline.generate_fallacy_report(args.process_id, args.output)
    
    elif args.command == 'list':
        process_ids = pipeline.db.get_all_process_ids()
        print("Available processes:")
        for pid in process_ids:
            process = pipeline.db.get_deliberation_process(pid)
            print(f"  - {pid}: {process.name} ({process.start_date.strftime('%Y-%m-%d')})")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
