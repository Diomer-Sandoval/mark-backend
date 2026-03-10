from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ...state import BrandDNAState
from .prompt import BrandDNAOutput, SYSTEM_PROMPT, USER_PROMPT


def ai_agent_node(state: BrandDNAState):
    if state.get("error"):
        return state

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.2)
    parser = JsonOutputParser(pydantic_object=BrandDNAOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm | parser

    try:
        response = chain.invoke({
            "data": state["preprocessed_data"],
            "format_instructions": parser.get_format_instructions(),
        })
        return {"llm_output": response}
    except Exception as e:
        return {"error": f"LLM parsing error: {str(e)}"}
