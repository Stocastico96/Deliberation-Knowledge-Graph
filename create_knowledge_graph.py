#!/usr/bin/env python3
"""
Script to create a unified knowledge graph from various deliberation datasets.
This script converts data from different sources into RDF format using the
deliberation ontology and combines them into a single knowledge graph.
"""

import os
import json
import csv
import sys
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD, OWL
import uuid

# Define namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# Base URI for resources
BASE_URI = "https://w3id.org/deliberation/resource/"

def create_unified_graph():
    """Create a unified RDF graph with all namespaces bound"""
    g = Graph()
    g.bind("del", DEL)
    g.bind("foaf", FOAF)
    g.bind("sioc", SIOC)
    g.bind("dc", DC)
    g.bind("skos", SKOS)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("owl", OWL)
    return g

def process_ep_debates(graph, file_path):
    """Process European Parliament debates data"""
    print(f"Processing European Parliament debates from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add deliberation process
        process_uri = URIRef(BASE_URI + data.get("del:identifier", data.get("dkg:identifier", f"ep_debate_{uuid.uuid4()}")))
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        
        # Add basic properties
        for prefix in ["del:", "dkg:"]:  # Try both prefixes for compatibility
            if f"{prefix}identifier" in data:
                graph.add((process_uri, DEL.identifier, Literal(data[f"{prefix}identifier"])))
            if f"{prefix}name" in data:
                graph.add((process_uri, DEL.name, Literal(data[f"{prefix}name"])))
            if f"{prefix}startDate" in data:
                graph.add((process_uri, DEL.startDate, Literal(data[f"{prefix}startDate"], datatype=XSD.dateTime)))
            if f"{prefix}endDate" in data:
                graph.add((process_uri, DEL.endDate, Literal(data[f"{prefix}endDate"], datatype=XSD.dateTime)))
        
        # Process topics
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasTopic" in data:
                for topic in data[f"{prefix}hasTopic"]:
                    topic_id = topic.get(f"{prefix}identifier", f"topic_{uuid.uuid4()}")
                    topic_uri = URIRef(BASE_URI + topic_id)
                    graph.add((topic_uri, RDF.type, DEL.Topic))
                    graph.add((topic_uri, DEL.identifier, Literal(topic_id)))
                    graph.add((topic_uri, DEL.name, Literal(topic.get(f"{prefix}name", ""))))
                    graph.add((process_uri, DEL.hasTopic, topic_uri))
        
        # Process participants
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasParticipant" in data:
                for participant in data[f"{prefix}hasParticipant"]:
                    participant_id = participant.get(f"{prefix}identifier", f"participant_{uuid.uuid4()}")
                    participant_uri = URIRef(BASE_URI + participant_id)
                    graph.add((participant_uri, RDF.type, DEL.Participant))
                    graph.add((participant_uri, DEL.identifier, Literal(participant_id)))
                    graph.add((participant_uri, DEL.name, Literal(participant.get(f"{prefix}name", ""))))
                    
                    # Add role if available
                    if f"{prefix}hasRole" in participant:
                        role = participant[f"{prefix}hasRole"]
                        role_uri = URIRef(BASE_URI + f"role_{participant_id}")
                        graph.add((role_uri, RDF.type, DEL.Role))
                        graph.add((role_uri, DEL.name, Literal(role.get(f"{prefix}name", ""))))
                        graph.add((participant_uri, DEL.hasRole, role_uri))
                    
                    # Add affiliation if available
                    if f"{prefix}isAffiliatedWith" in participant:
                        org = participant[f"{prefix}isAffiliatedWith"]
                        org_name = org.get(f"{prefix}name", "")
                        org_uri = URIRef(BASE_URI + f"org_{org_name.replace(' ', '_').replace('/', '_')}")
                        graph.add((org_uri, RDF.type, DEL.Organization))
                        graph.add((org_uri, DEL.name, Literal(org_name)))
                        graph.add((participant_uri, DEL.isAffiliatedWith, org_uri))
                    
                    graph.add((process_uri, DEL.hasParticipant, participant_uri))
        
        # Process contributions
        for prefix in ["del:", "dkg:"]:
            if f"{prefix}hasContribution" in data:
                for contribution in data[f"{prefix}hasContribution"]:
                    contribution_id = contribution.get(f"{prefix}identifier", f"contribution_{uuid.uuid4()}")
                    contribution_uri = URIRef(BASE_URI + contribution_id)
                    graph.add((contribution_uri, RDF.type, DEL.Contribution))
                    graph.add((contribution_uri, DEL.identifier, Literal(contribution_id)))
                    graph.add((contribution_uri, DEL.text, Literal(contribution.get(f"{prefix}text", ""))))
                    
                    # Add timestamp if available
                    if f"{prefix}timestamp" in contribution:
                        graph.add((contribution_uri, DEL.timestamp, 
                                  Literal(contribution[f"{prefix}timestamp"], datatype=XSD.dateTime)))
                    
                    # Link to participant
                    if f"{prefix}madeBy" in contribution and "@id" in contribution[f"{prefix}madeBy"]:
                        participant_id = contribution[f"{prefix}madeBy"]["@id"]
                        participant_uri = URIRef(BASE_URI + participant_id)
                        graph.add((contribution_uri, DEL.madeBy, participant_uri))
                    
                    # Link contribution to process
                    graph.add((process_uri, DEL.hasContribution, contribution_uri))
        
        print(f"Successfully processed European Parliament debates: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing European Parliament debates: {str(e)}")
        return False

def process_decide_madrid(graph, file_path):
    """Process Decide Madrid data"""
    print(f"Processing Decide Madrid data from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a deliberation process for the platform
        process_uri = URIRef(BASE_URI + "decide_madrid_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("decide_madrid_process")))
        graph.add((process_uri, DEL.name, Literal("Decide Madrid Participatory Democracy Platform")))
        
        # Process proposals
        if "proposals" in data:
            for proposal in data["proposals"]:
                # Create a topic for each proposal
                proposal_id = str(proposal.get("id", uuid.uuid4()))
                topic_uri = URIRef(BASE_URI + f"madrid_topic_{proposal_id}")
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(f"madrid_topic_{proposal_id}")))
                graph.add((topic_uri, DEL.name, Literal(proposal.get("title", ""))))
                graph.add((process_uri, DEL.hasTopic, topic_uri))
                
                # Create a contribution for the proposal content
                contribution_uri = URIRef(BASE_URI + f"madrid_proposal_{proposal_id}")
                graph.add((contribution_uri, RDF.type, DEL.Contribution))
                graph.add((contribution_uri, DEL.identifier, Literal(f"madrid_proposal_{proposal_id}")))
                graph.add((contribution_uri, DEL.text, Literal(proposal.get("summary", ""))))
                
                # Add author as participant
                if "author" in proposal:
                    author = proposal["author"]
                    author_id = str(author.get("id", uuid.uuid4()))
                    participant_uri = URIRef(BASE_URI + f"madrid_participant_{author_id}")
                    graph.add((participant_uri, RDF.type, DEL.Participant))
                    graph.add((participant_uri, DEL.identifier, Literal(f"madrid_participant_{author_id}")))
                    graph.add((participant_uri, DEL.name, Literal(author.get("username", ""))))
                    graph.add((process_uri, DEL.hasParticipant, participant_uri))
                    graph.add((contribution_uri, DEL.madeBy, participant_uri))
                
                # Link contribution to process and topic
                graph.add((process_uri, DEL.hasContribution, contribution_uri))
                graph.add((contribution_uri, DEL.hasTopic, topic_uri))
                
                # Process comments
                if "comments" in proposal:
                    for comment in proposal["comments"]:
                        comment_id = str(comment.get("id", uuid.uuid4()))
                        comment_uri = URIRef(BASE_URI + f"madrid_comment_{comment_id}")
                        graph.add((comment_uri, RDF.type, DEL.Contribution))
                        graph.add((comment_uri, DEL.identifier, Literal(f"madrid_comment_{comment_id}")))
                        graph.add((comment_uri, DEL.text, Literal(comment.get("body", ""))))
                        
                        # Add comment author
                        if "author" in comment:
                            c_author = comment["author"]
                            c_author_id = str(c_author.get("id", uuid.uuid4()))
                            c_participant_uri = URIRef(BASE_URI + f"madrid_participant_{c_author_id}")
                            graph.add((c_participant_uri, RDF.type, DEL.Participant))
                            graph.add((c_participant_uri, DEL.identifier, Literal(f"madrid_participant_{c_author_id}")))
                            graph.add((c_participant_uri, DEL.name, Literal(c_author.get("username", ""))))
                            graph.add((process_uri, DEL.hasParticipant, c_participant_uri))
                            graph.add((comment_uri, DEL.madeBy, c_participant_uri))
                        
                        # Link comment to proposal and process
                        graph.add((comment_uri, DEL.responseTo, contribution_uri))
                        graph.add((process_uri, DEL.hasContribution, comment_uri))
        
        print(f"Successfully processed Decide Madrid data: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing Decide Madrid data: {str(e)}")
        return False

def process_delidata(graph, file_path):
    """Process DeliData dataset"""
    print(f"Processing DeliData from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a deliberation process for each conversation
        if "conversations" in data:
            for conversation in data["conversations"]:
                conv_id = str(conversation.get("id", uuid.uuid4()))
                process_uri = URIRef(BASE_URI + f"delidata_process_{conv_id}")
                graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
                graph.add((process_uri, DEL.identifier, Literal(f"delidata_process_{conv_id}")))
                graph.add((process_uri, DEL.name, Literal(f"DeliData Conversation {conv_id}")))
                
                # Add topic
                if "topic" in conversation:
                    topic_uri = URIRef(BASE_URI + f"delidata_topic_{conv_id}")
                    graph.add((topic_uri, RDF.type, DEL.Topic))
                    graph.add((topic_uri, DEL.identifier, Literal(f"delidata_topic_{conv_id}")))
                    graph.add((topic_uri, DEL.name, Literal(conversation["topic"])))
                    graph.add((process_uri, DEL.hasTopic, topic_uri))
                
                # Process participants
                participants = {}
                if "participants" in conversation:
                    for participant in conversation["participants"]:
                        p_id = str(participant.get("id", uuid.uuid4()))
                        participant_uri = URIRef(BASE_URI + f"delidata_participant_{p_id}")
                        graph.add((participant_uri, RDF.type, DEL.Participant))
                        graph.add((participant_uri, DEL.identifier, Literal(f"delidata_participant_{p_id}")))
                        graph.add((participant_uri, DEL.name, Literal(participant.get("name", f"Participant {p_id}"))))
                        graph.add((process_uri, DEL.hasParticipant, participant_uri))
                        participants[p_id] = participant_uri
                
                # Process messages
                if "messages" in conversation:
                    for message in conversation["messages"]:
                        msg_id = str(message.get("id", uuid.uuid4()))
                        msg_uri = URIRef(BASE_URI + f"delidata_message_{msg_id}")
                        graph.add((msg_uri, RDF.type, DEL.Contribution))
                        graph.add((msg_uri, DEL.identifier, Literal(f"delidata_message_{msg_id}")))
                        graph.add((msg_uri, DEL.text, Literal(message.get("text", ""))))
                        
                        # Add timestamp if available
                        if "timestamp" in message:
                            graph.add((msg_uri, DEL.timestamp, Literal(message["timestamp"], datatype=XSD.dateTime)))
                        
                        # Link to participant
                        if "participant_id" in message and message["participant_id"] in participants:
                            graph.add((msg_uri, DEL.madeBy, participants[message["participant_id"]]))
                        
                        # Link to parent message if it's a reply
                        if "reply_to" in message and message["reply_to"]:
                            reply_to_uri = URIRef(BASE_URI + f"delidata_message_{message['reply_to']}")
                            graph.add((msg_uri, DEL.responseTo, reply_to_uri))
                        
                        # Link message to process
                        graph.add((process_uri, DEL.hasContribution, msg_uri))
        
        print(f"Successfully processed DeliData: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing DeliData: {str(e)}")
        return False

def process_eu_have_your_say(graph, file_path):
    """Process EU Have Your Say data"""
    print(f"Processing EU Have Your Say data from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Create a deliberation process for the platform
        process_uri = URIRef(BASE_URI + "eu_have_your_say_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("eu_have_your_say_process")))
        graph.add((process_uri, DEL.name, Literal("EU Have Your Say Public Consultation Platform")))
        
        # Process each consultation as a topic
        topics = {}
        for row in rows:
            initiative_id = row.get("Initiative ID", str(uuid.uuid4()))
            
            # Create topic if not exists
            if initiative_id not in topics:
                topic_uri = URIRef(BASE_URI + f"euhys_topic_{initiative_id}")
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(f"euhys_topic_{initiative_id}")))
                graph.add((topic_uri, DEL.name, Literal(row.get("Initiative Title", f"Initiative {initiative_id}"))))
                graph.add((process_uri, DEL.hasTopic, topic_uri))
                topics[initiative_id] = topic_uri
            
            # Create participant
            participant_id = row.get("Contributor ID", str(uuid.uuid4()))
            participant_uri = URIRef(BASE_URI + f"euhys_participant_{participant_id}")
            graph.add((participant_uri, RDF.type, DEL.Participant))
            graph.add((participant_uri, DEL.identifier, Literal(f"euhys_participant_{participant_id}")))
            graph.add((participant_uri, DEL.name, Literal(row.get("Contributor Name", f"Contributor {participant_id}"))))
            
            # Add organization if available
            if "Organization" in row and row["Organization"]:
                org_uri = URIRef(BASE_URI + f"euhys_org_{row['Organization'].replace(' ', '_')}")
                graph.add((org_uri, RDF.type, DEL.Organization))
                graph.add((org_uri, DEL.name, Literal(row["Organization"])))
                graph.add((participant_uri, DEL.isAffiliatedWith, org_uri))
            
            graph.add((process_uri, DEL.hasParticipant, participant_uri))
            
            # Create contribution
            feedback_id = row.get("Feedback ID", str(uuid.uuid4()))
            contribution_uri = URIRef(BASE_URI + f"euhys_feedback_{feedback_id}")
            graph.add((contribution_uri, RDF.type, DEL.Contribution))
            graph.add((contribution_uri, DEL.identifier, Literal(f"euhys_feedback_{feedback_id}")))
            graph.add((contribution_uri, DEL.text, Literal(row.get("Feedback Text", ""))))
            
            # Add timestamp if available
            if "Submission Date" in row:
                graph.add((contribution_uri, DEL.timestamp, Literal(row["Submission Date"], datatype=XSD.date)))
            
            # Link contribution to participant, topic and process
            graph.add((contribution_uri, DEL.madeBy, participant_uri))
            graph.add((contribution_uri, DEL.hasTopic, topics[initiative_id]))
            graph.add((process_uri, DEL.hasContribution, contribution_uri))
        
        print(f"Successfully processed EU Have Your Say data: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing EU Have Your Say data: {str(e)}")
        return False

def process_habermas_machine(graph, file_path):
    """Process Habermas Machine data"""
    print(f"Processing Habermas Machine data from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a deliberation process
        process_uri = URIRef(BASE_URI + "habermas_machine_process")
        graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
        graph.add((process_uri, DEL.identifier, Literal("habermas_machine_process")))
        graph.add((process_uri, DEL.name, Literal("Habermas Machine Deliberative Democracy Experiment")))
        
        # Process discussions
        if "discussions" in data:
            for discussion in data["discussions"]:
                disc_id = str(discussion.get("id", uuid.uuid4()))
                
                # Create topic
                topic_uri = URIRef(BASE_URI + f"habermas_topic_{disc_id}")
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(f"habermas_topic_{disc_id}")))
                graph.add((topic_uri, DEL.name, Literal(discussion.get("title", f"Discussion {disc_id}"))))
                graph.add((process_uri, DEL.hasTopic, topic_uri))
                
                # Process participants
                participants = {}
                if "participants" in discussion:
                    for participant in discussion["participants"]:
                        p_id = str(participant.get("id", uuid.uuid4()))
                        participant_uri = URIRef(BASE_URI + f"habermas_participant_{p_id}")
                        graph.add((participant_uri, RDF.type, DEL.Participant))
                        graph.add((participant_uri, DEL.identifier, Literal(f"habermas_participant_{p_id}")))
                        graph.add((participant_uri, DEL.name, Literal(participant.get("name", f"Participant {p_id}"))))
                        
                        # Add role if available
                        if "role" in participant:
                            role_uri = URIRef(BASE_URI + f"habermas_role_{participant['role'].replace(' ', '_')}")
                            graph.add((role_uri, RDF.type, DEL.Role))
                            graph.add((role_uri, DEL.name, Literal(participant["role"])))
                            graph.add((participant_uri, DEL.hasRole, role_uri))
                        
                        graph.add((process_uri, DEL.hasParticipant, participant_uri))
                        participants[p_id] = participant_uri
                
                # Process utterances
                if "utterances" in discussion:
                    for utterance in discussion["utterances"]:
                        utt_id = str(utterance.get("id", uuid.uuid4()))
                        utt_uri = URIRef(BASE_URI + f"habermas_utterance_{utt_id}")
                        graph.add((utt_uri, RDF.type, DEL.Contribution))
                        graph.add((utt_uri, DEL.identifier, Literal(f"habermas_utterance_{utt_id}")))
                        graph.add((utt_uri, DEL.text, Literal(utterance.get("text", ""))))
                        
                        # Add timestamp if available
                        if "timestamp" in utterance:
                            graph.add((utt_uri, DEL.timestamp, Literal(utterance["timestamp"], datatype=XSD.dateTime)))
                        
                        # Link to participant
                        if "speaker_id" in utterance and utterance["speaker_id"] in participants:
                            graph.add((utt_uri, DEL.madeBy, participants[utterance["speaker_id"]]))
                        
                        # Link to parent utterance if it's a response
                        if "response_to" in utterance and utterance["response_to"]:
                            response_to_uri = URIRef(BASE_URI + f"habermas_utterance_{utterance['response_to']}")
                            graph.add((utt_uri, DEL.responseTo, response_to_uri))
                        
                        # Link utterance to process and topic
                        graph.add((process_uri, DEL.hasContribution, utt_uri))
                        graph.add((utt_uri, DEL.hasTopic, topic_uri))
                        
                        # Add argument structure if available
                        if "argument_type" in utterance:
                            arg_uri = URIRef(BASE_URI + f"habermas_argument_{utt_id}")
                            graph.add((arg_uri, RDF.type, DEL.Argument))
                            graph.add((arg_uri, DEL.identifier, Literal(f"habermas_argument_{utt_id}")))
                            graph.add((arg_uri, DEL.text, Literal(utterance.get("text", ""))))
                            
                            # Link argument to contribution
                            graph.add((utt_uri, DEL.hasArgument, arg_uri))
                            
                            # Add premise and conclusion
                            if "premise" in utterance:
                                premise_uri = URIRef(BASE_URI + f"habermas_premise_{utt_id}")
                                graph.add((premise_uri, RDF.type, DEL.Premise))
                                graph.add((premise_uri, DEL.text, Literal(utterance["premise"])))
                                graph.add((arg_uri, DEL.hasPremise, premise_uri))
                            
                            if "conclusion" in utterance:
                                conclusion_uri = URIRef(BASE_URI + f"habermas_conclusion_{utt_id}")
                                graph.add((conclusion_uri, RDF.type, DEL.Conclusion))
                                graph.add((conclusion_uri, DEL.text, Literal(utterance["conclusion"])))
                                graph.add((arg_uri, DEL.hasConclusion, conclusion_uri))
        
        print(f"Successfully processed Habermas Machine data: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing Habermas Machine data: {str(e)}")
        return False

def process_us_supreme_court(graph, file_path):
    """Process US Supreme Court Arguments data"""
    print(f"Processing US Supreme Court Arguments from {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create a deliberation process for each case
        if "cases" in data:
            for case in data["cases"]:
                case_id = str(case.get("docket_number", uuid.uuid4())).replace(" ", "_")
                process_uri = URIRef(BASE_URI + f"scotus_case_{case_id}")
                graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
                graph.add((process_uri, DEL.identifier, Literal(f"scotus_case_{case_id}")))
                graph.add((process_uri, DEL.name, Literal(case.get("case_name", f"Case {case_id}"))))
                
                # Add date if available
                if "argument_date" in case:
                    graph.add((process_uri, DEL.startDate, Literal(case["argument_date"], datatype=XSD.date)))
                
                # Create topic
                topic_uri = URIRef(BASE_URI + f"scotus_topic_{case_id}")
                graph.add((topic_uri, RDF.type, DEL.Topic))
                graph.add((topic_uri, DEL.identifier, Literal(f"scotus_topic_{case_id}")))
                graph.add((topic_uri, DEL.name, Literal(case.get("issue_area", "Legal Argument"))))
                graph.add((process_uri, DEL.hasTopic, topic_uri))
                
                # Process participants (justices and advocates)
                participants = {}
                
                # Add justices
                if "justices" in case:
                    for justice in case["justices"]:
                        j_id = str(justice.get("id", uuid.uuid4()))
                        justice_uri = URIRef(BASE_URI + f"scotus_justice_{j_id}")
                        graph.add((justice_uri, RDF.type, DEL.Participant))
                        graph.add((justice_uri, DEL.identifier, Literal(f"scotus_justice_{j_id}")))
                        graph.add((justice_uri, DEL.name, Literal(justice.get("name", f"Justice {j_id}"))))
                        
                        # Add role
                        role_uri = URIRef(BASE_URI + "scotus_role_justice")
                        graph.add((role_uri, RDF.type, DEL.Role))
                        graph.add((role_uri, DEL.name, Literal("Justice")))
                        graph.add((justice_uri, DEL.hasRole, role_uri))
                        
                        graph.add((process_uri, DEL.hasParticipant, justice_uri))
                        participants[j_id] = justice_uri
                
                # Add advocates
                if "advocates" in case:
                    for advocate in case["advocates"]:
                        a_id = str(advocate.get("id", uuid.uuid4()))
                        advocate_uri = URIRef(BASE_URI + f"scotus_advocate_{a_id}")
                        graph.add((advocate_uri, RDF.type, DEL.Participant))
                        graph.add((advocate_uri, DEL.identifier, Literal(f"scotus_advocate_{a_id}")))
                        graph.add((advocate_uri, DEL.name, Literal(advocate.get("name", f"Advocate {a_id}"))))
                        
                        # Add role
                        role_uri = URIRef(BASE_URI + f"scotus_role_{advocate.get('role', 'advocate').replace(' ', '_')}")
                        graph.add((role_uri, RDF.type, DEL.Role))
                        graph.add((role_uri, DEL.name, Literal(advocate.get("role", "Advocate"))))
                        graph.add((advocate_uri, DEL.hasRole, role_uri))
                        
                        # Add affiliation if available
                        if "representing" in advocate:
                            org_uri = URIRef(BASE_URI + f"scotus_party_{advocate['representing'].replace(' ', '_')}")
                            graph.add((org_uri, RDF.type, DEL.Organization))
                            graph.add((org_uri, DEL.name, Literal(advocate["representing"])))
                            graph.add((advocate_uri, DEL.isAffiliatedWith, org_uri))
                        
                        graph.add((process_uri, DEL.hasParticipant, advocate_uri))
                        participants[a_id] = advocate_uri
                
                # Process utterances
                if "transcript" in case:
                    for utterance in case["transcript"]:
                        utt_id = str(utterance.get("id", uuid.uuid4()))
                        utt_uri = URIRef(BASE_URI + f"scotus_utterance_{utt_id}")
                        graph.add((utt_uri, RDF.type, DEL.Contribution))
                        graph.add((utt_uri, DEL.identifier, Literal(f"scotus_utterance_{utt_id}")))
                        graph.add((utt_uri, DEL.text, Literal(utterance.get("text", ""))))
                        
                        # Link to speaker
                        if "speaker_id" in utterance and utterance["speaker_id"] in participants:
                            graph.add((utt_uri, DEL.madeBy, participants[utterance["speaker_id"]]))
                        
                        # Link utterance to process
                        graph.add((process_uri, DEL.hasContribution, utt_uri))
        
        print(f"Successfully processed US Supreme Court Arguments: {len(graph)} triples")
        return True
    
    except Exception as e:
        print(f"Error processing US Supreme Court Arguments: {str(e)}")
        return False

def main():
    """Main function to create the knowledge graph and set up SPARQL endpoint"""
    # Create unified graph
    graph = create_unified_graph()
    
    # Process datasets
    datasets = [
        {
            "name": "European Parliament Debates",
            "function": process_ep_debates,
            "file_path": "data/EU_parliament_debates/ep_debates/debate_2025-03-10.json"
        },
        {
            "name": "European Parliament Debates 2025-03-11",
            "function": process_ep_debates,
            "file_path": "data/EU_parliament_debates/ep_debates/debate_2025-03-11.json"
        },
        {
            "name": "European Parliament Debates 2025-03-12",
            "function": process_ep_debates,
            "file_path": "data/EU_parliament_debates/ep_debates/debate_2025-03-12.json"
        },
        {
            "name": "Decide Madrid",
            "function": process_decide_madrid,
            "file_path": "data/decide_Madrid/sample/sample.json"
        },
        {
            "name": "DeliData",
            "function": process_delidata,
            "file_path": "data/delidata/sample/sample.json"
        },
        {
            "name": "EU Have Your Say",
            "function": process_eu_have_your_say,
            "file_path": "data/EU_have_your_say/sample/sample.csv"
        },
        {
            "name": "Habermas Machine",
            "function": process_habermas_machine,
            "file_path": "data/habermas_machine/sample/sample.json"
        },
        {
            "name": "US Supreme Court Arguments",
            "function": process_us_supreme_court,
            "file_path": "data/US_supreme_court_arguments/sample/sample.json"
        }
    ]
    
    # Process each dataset
    for dataset in datasets:
        print(f"\nProcessing {dataset['name']}...")
        if os.path.exists(dataset["file_path"]):
            dataset["function"](graph, dataset["file_path"])
        else:
            print(f"Warning: File {dataset['file_path']} does not exist. Skipping {dataset['name']}.")
    
    # Save the unified graph to a file
    output_dir = "knowledge_graph"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save in different formats
    graph.serialize(destination=f"{output_dir}/deliberation_kg.ttl", format="turtle")
    graph.serialize(destination=f"{output_dir}/deliberation_kg.rdf", format="xml")
    graph.serialize(destination=f"{output_dir}/deliberation_kg.jsonld", format="json-ld")
    
    print(f"\nKnowledge graph created with {len(graph)} triples")
    print(f"Saved to {output_dir}/deliberation_kg.ttl, {output_dir}/deliberation_kg.rdf, and {output_dir}/deliberation_kg.jsonld")
    
    # Instructions for setting up SPARQL endpoint
    print("\nTo set up a SPARQL endpoint, follow these steps:")
    print("1. Download Apache Jena Fuseki from https://jena.apache.org/download/")
    print("2. Extract the downloaded archive")
    print("3. Start Fuseki server: ./fuseki-server --mem /deliberation")
    print("4. Upload the knowledge graph file (deliberation_kg.ttl) through the web interface at http://localhost:3030/")
    print("5. You can then query the SPARQL endpoint at http://localhost:3030/deliberation/sparql")
    
    # Example SPARQL queries
    print("\nExample SPARQL queries:")
    print("""
    # Query 1: List all deliberation processes
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    
    SELECT ?process ?name
    WHERE {
        ?process a del:DeliberationProcess ;
                 del:name ?name .
    }
    
    # Query 2: Find all contributions by a specific participant
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    
    SELECT ?contribution ?text
    WHERE {
        ?contribution a del:Contribution ;
                     del:text ?text ;
                     del:madeBy ?participant .
        ?participant del:name "Iratxe García Pérez" .
    }
    
    # Query 3: Find all topics discussed in European Parliament debates
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    
    SELECT ?topic ?name
    WHERE {
        ?process a del:DeliberationProcess ;
                 del:name ?processName ;
                 del:hasTopic ?topic .
        ?topic del:name ?name .
        FILTER(CONTAINS(?processName, "European Parliament"))
    }
    """)

if __name__ == "__main__":
    main()
