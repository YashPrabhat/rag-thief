from target_rag_app.rag_system import create_rag_chain
from attacker_agent.agent import RAGThiefAgent

def main():
    # 1. Set up the target RAG application
    print("Setting up the target RAG application...")
    target_chain = create_rag_chain()
    
    # 2. Initialize the RAG-Thief agent with the target
    attacker = RAGThiefAgent(target_rag_chain=target_chain)

    # 3. Launch the attack
    attacker.execute_attack(num_iterations=10) # Let's do 10 iterations for a quick test

if __name__ == '__main__':
    main()