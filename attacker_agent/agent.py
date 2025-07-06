import os
import re
import time
import collections
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from . import prompts

class RAGThiefAgent:
    def __init__(self, target_rag_chain):
        load_dotenv()
        self.target_rag_chain = target_rag_chain

        # The agent's own brain for reflection
        self.attacker_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",  # Use the same model as the target RA
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.5
        )

        # Memory modules
        self.short_term_memory = collections.deque()
        self.long_term_memory = set()

        print("[Attacker Agent] Initialized RAG-Thief.")

    def _parse_leaked_chunks(self, response_text):
        """
        Extracts content from markdown code blocks in the response.
        This needs to be tailored to the expected output of the leakage prompt.
        """
        # Regex to find content inside ``` ... ```
        matches = re.findall(r"```(.*?)```", response_text, re.DOTALL)
        # Clean up the extracted text
        leaked_content = [match.strip() for match in matches]
        if leaked_content:
            # We'll just join it all and treat it as one found chunk for simplicity
            return " ".join(leaked_content)
        return None

    def _reflect_and_get_new_queries(self, chunk):
        """
        Uses the attacker's LLM to generate new anchor queries from a chunk.
        """
        reflection_prompt = prompts.UNTARGETED_REFLECTION_PROMPT_TEMPLATE.format(chunk=chunk)
        try:
            response = self.attacker_llm.invoke(reflection_prompt)
            # Split the response into individual lines/queries
            new_queries = [line.strip() for line in response.content.split('\n') if line.strip()]
            return new_queries
        except Exception as e:
            print(f"[Attacker Agent] Reflection failed: {e}")
            return []

    def execute_attack(self, num_iterations=20):
        print("\n" + "="*50)
        print("         STARTING RAG-THIEF ATTACK")
        print("="*50 + "\n")
        
        # 1. Start with an initial adversarial query
        initial_anchor = "Tell me everything about the project."
        initial_query = f"{initial_anchor}\n\n{prompts.ADVERSARIAL_COMMAND}"
        
        # Use the initial query as the first item to process
        items_to_process = collections.deque([initial_query])

        for i in range(num_iterations):
            if not items_to_process:
                print(f"[Attacker Agent] Iteration {i+1}/{num_iterations}: No more items to process. Ending attack.")
                break
            
            current_item = items_to_process.popleft()
            print(f"\n--- Iteration {i+1}/{num_iterations} ---")

            # 2. Decide if we are reflecting or using the initial query
            if "ADVERSARIAL_COMMAND" in current_item:
                # This is a full query string, not a chunk for reflection
                query_to_send = current_item
                print(f"Action: Sending a constructed query.")
            else:
                # This is a chunk from memory; we need to reflect on it
                print(f"Action: Reflecting on a new chunk of size {len(current_item)}...")
                new_anchor_queries = self._reflect_and_get_new_queries(current_item)
                if not new_anchor_queries:
                    print("Reflection yielded no new queries. Skipping.")
                    continue
                
                # Create a new full adversarial query from the first reflection
                new_anchor = new_anchor_queries[0]
                query_to_send = f"{new_anchor}\n\n{prompts.ADVERSARIAL_COMMAND}"
                print(f"Generated new anchor: '{new_anchor[:50]}...'")

            # 3. Attack the Target RAG
            try:
                response = self.target_rag_chain({"query": query_to_send})
                response_text = response['result']
            except Exception as e:
                print(f"Query to target failed: {e}")
                time.sleep(10) # Wait if there's an API error
                continue
            
            # 4. Parse the response for leaked chunks
            leaked_chunk = self._parse_leaked_chunks(response_text)
            
            if leaked_chunk and leaked_chunk not in self.long_term_memory:
                print(f"SUCCESS: Extracted a new chunk of size {len(leaked_chunk)}!")
                self.long_term_memory.add(leaked_chunk)
                items_to_process.append(leaked_chunk) # Add to queue for future reflection
            elif leaked_chunk:
                print("INFO: Extracted a chunk, but it was a duplicate.")
            else:
                print("FAILURE: No new chunk was extracted in this iteration.")
                
            # Respect API rate limits
            time.sleep(2) 
        
        self._report_results()

    def _report_results(self):
        print("\n" + "="*50)
        print("           RAG-THIEF ATTACK COMPLETE")
        print("="*50 + "\n")
        print(f"Total unique chunks extracted: {len(self.long_term_memory)}\n")
        print("--- Extracted Content ---")
        for idx, chunk in enumerate(self.long_term_memory):
            print(f"Chunk {idx+1}: {chunk}\n")
        print("-------------------------\n")
        all_sentences = set()
        for chunk in self.long_term_memory:
            sentences = chunk.split('.') # Simple split by sentence
            for s in sentences:
                if s.strip():
                    all_sentences.add(s.strip())

        print("--- Unique Sentences Found ---")
        for sentence in sorted(list(all_sentences)):
            print(f"- {sentence}")
        print("-----------------------------\n")
        # --- END OF NEW REPORT ---

        # You can keep the old report too if you like
        # print("--- Raw Extracted Chunks ---")
        # ...