from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import BaseChatModel
from langgraph.config import RunnableConfig
from .formatter import report_formatter

from .state import (
    CodeInspectorSchema,
    CodeProfılerSchema,
    CodeScorerSchema,
    AnalysisReport,
    NodeFlag,
    State
)

PROFILER_SYSTEM_MSG = (
    "You are an AI developer that analyzes the code given to you and produces a detailed analysis report about the code. "
    "IMPORTANT: The input code is formatted with line numbers at the beginning of each line (e.g., '12 | code_line') solely to help you identify and calculate exact line ranges. "
    "These line numbers are NOT part of the actual code. You must ignore these prefix numbers for all other tasks; do not treat them as syntax errors or lint warnings. "
    "Furthermore, you must NEVER include these line numbers in any output code fields, such as 'original_code', 'suggested_code', or 'fixed_code'."
)


INSPECTOR_SYSTEM_MSG = (
    "You are an AI developer that debug the code given to you and find the errors, potential errors, suggestions and produced a detailed error report about the code. "
    "IMPORTANT: The input code is formatted with line numbers at the beginning of each line (e.g., '12 | code_line') solely to help you identify and calculate exact line ranges. "
    "These line numbers are NOT part of the actual code. You must ignore these prefix numbers for all other tasks; do not treat them as syntax errors or lint warnings. "
    "Furthermore, you must NEVER include these line numbers in any output code fields, such as 'original_code', 'suggested_code', or 'fixed_code'."
)


SCORER_SYSTEM_MSG = (
    "You are an AI developer that receives the code and reports given to you and the report generated about that code, and assigns specific scores to the code based on these characteristics. "
    "IMPORTANT: The input code is formatted with line numbers at the beginning of each line (e.g., '12 | code_line') solely to help you identify and calculate exact line ranges. "
    "These line numbers are NOT part of the actual code. You must ignore these prefix numbers for all other tasks; do not treat them as syntax errors or lint warnings. "
    "Furthermore, you must NEVER include these line numbers in any output code fields, such as 'original_code', 'suggested_code', or 'fixed_code'."
)

REPORTER_SYSTEM_MSG = (
    "You are an AI developer that takes a given piece of code along with its generated reports, and consolidates them into a single, clean, and human-readable comprehensive Markdown report. "
    "IMPORTANT: The input code is formatted with line numbers at the beginning of each line (e.g., '12 | code_line') solely to help you identify and calculate exact line ranges. "
    "These line numbers are NOT part of the actual code. You must ignore these prefix numbers for all other tasks; do not treat them as syntax errors or lint warnings. "
    "Furthermore, you must NEVER include these line numbers in any output code fields, such as 'original_code', 'suggested_code', or 'fixed_code'."
)

def get_analyzer_graph(llm: BaseChatModel):
    """
    Args:
       llm(BaseChatModel):
    
    Get the code analyzer graph. 
    
    """

    profiler_llm = llm.with_structured_output(CodeProfılerSchema)
    inspector_llm = llm.with_structured_output(CodeInspectorSchema)
    scorer_llm = llm.with_structured_output(CodeScorerSchema)

    def _profiler_worker_node(state: State, config: RunnableConfig):
        callback = config.get("configurable", "").get("callback", "")
        formatted_reports = report_formatter(code = state["code"])

        if callback:
            flag = NodeFlag(worker_name = "profiler", flag = True)
            callback(flag)

        if formatted_reports:
            profiler_report = profiler_llm.invoke(
                input = [
                    SystemMessage(content = PROFILER_SYSTEM_MSG),
                    HumanMessage(content = formatted_reports)
                ]
            )

            if callback:
                analysis_report = AnalysisReport(profiler_report = profiler_report)
                flag = NodeFlag(worker_name = "profiler", flag = False)
                callback(flag)
                callback(analysis_report)

            return {"profiler_report": profiler_report}

        if callback:
            flag = NodeFlag(worker_name = "profiler", flag = False)
            callback(flag)
        
        return {"profiler_report": None}


    def _inspector_worker_node(state: State, config: RunnableConfig):
        callback = config.get("configurable", "").get("callback", "")
        formatted_reports = report_formatter(code = state["code"])

        if callback:
            flag = NodeFlag(worker_name = "inspector", flag = True)
            callback(flag)

        if formatted_reports:
            inspector_report = inspector_llm.invoke(
                input = [
                    SystemMessage(content = INSPECTOR_SYSTEM_MSG),
                    HumanMessage(content = formatted_reports)
                ]
            )

            if callback:
                analysis_report = AnalysisReport(inspector_report = inspector_report)
                flag = NodeFlag(worker_name = "inspector", flag = False)
                callback(flag)
                callback(analysis_report)

            return {"inspector_report": inspector_report}

        if callback:
            flag = NodeFlag(worker_name = "inspector", flag = False)
            callback(flag)
        
        return {"inspector_report": None}


    def _scorer_worker_node(state: State, config: RunnableConfig):
        callback = config.get("configurable", "").get("callback", "")

        formatted_reports = report_formatter(
            profiler_report = state["profiler_report"],
            inspector_report = state["inspector_report"],
            code = state["code"]
        )

        if callback:
            flag = NodeFlag(worker_name = "scorer", flag = True)
            callback(flag)
        
        if formatted_reports:
            scorer_report = scorer_llm.invoke(
                input = [
                    SystemMessage(content = SCORER_SYSTEM_MSG),
                    HumanMessage(content = formatted_reports)
                ]
            )
                
            if callback:
                analysis_report = AnalysisReport(scorer_report = scorer_report)
                flag = NodeFlag(worker_name = "scorer", flag = False)
                callback(flag)
                callback(analysis_report)

            return {"scorer_report": scorer_report}
        
        if callback:
            flag = NodeFlag(worker_name = "scorer", flag = False)
            callback(flag)
        
        return {"scorer_report": None}


    def _final_reporter_node(state: State, config: RunnableConfig):
        callback = config.get("configurable", "").get("callback", "")

        formatted_reports = report_formatter(
            scorer_report = state["scorer_report"] ,
            profiler_report = state["profiler_report"],
            inspector_report = state["inspector_report"],
            code = state["code"]
        )

        if callback:
            flag = NodeFlag(worker_name = "final_reporter", flag = True)
            callback(flag)
        
        if formatted_reports:
            final_report = llm.invoke(
                input = [
                    SystemMessage(content = REPORTER_SYSTEM_MSG),
                    HumanMessage(content = formatted_reports)
                ]
            )

            if callback:
                analysis_report = AnalysisReport(final_report = final_report.content)
                flag = NodeFlag(worker_name = "final_reporter", flag = False)
                callback(flag)
                callback(analysis_report)

            return {"final_report": final_report.content, "formatted_reports": formatted_reports}
        
        if callback:
            flag = NodeFlag(worker_name = "final_reporter", flag = False)
            callback(flag)

        return {"final_report": None, "formatted_reports": None}

    analyzer_graph = (
        StateGraph(State)
        .add_node("profiler", _profiler_worker_node)
        .add_node("inspector", _inspector_worker_node)
        .add_node("scorer", _scorer_worker_node)
        .add_node("final_reporter", _final_reporter_node)
        .add_edge(START, "profiler")
        .add_edge(START, "inspector")
        .add_edge("profiler", "scorer")
        .add_edge("inspector", "scorer")
        .add_edge("scorer", "final_reporter")
        .add_edge("final_reporter", END)
        .compile()
    )

    return analyzer_graph
