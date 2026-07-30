from typing import Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from dataclasses import dataclass

SEVERITY_TYPE = Literal["LOW", "MEDİUM", "HİGH", "CRİTİCAL"]
EFFORT_TYPE = Literal["QUİCK", "BALANCED", "ADVANCE"]
NODE_NAMES = Literal["inspector", "scorer", "profiler", "final_reporter"]

class Error(BaseModel):
    title: str = Field(
        description = "A concise headline or title summarizing the detected error.",
    )
    error_type: str = Field(
        description = "The technical type, name, or exception class of the error as defined within the respective programming language."
    )

    line_range: tuple[int, int] = Field(
        description = (
            "The specific starting and ending line numbers of the code where the error occurs, represented as a tuple [start_line, end_line]. "
            "IMPORTANT: You must always provide a tuple. If the error is on a single line (e.g., line 1), return it as (1, 1). "
            "If the error spans multiple lines (e.g., from line 12 to 16), return it as (12, 16)."
        ),
        examples = [(1, 1), (2, 23), (3, 6)]
    )

    error_reason: str = Field(
        description = "A brief, clear explanation of the root cause behind the occurrence of this error.",
    )
    fix_suggestion: str = Field(
        description = "A brief and actionable suggestion, description text explaining how to resolve the error",
    )
    fixed_code: str = Field(
        description = (
            "The production-ready, copy-pasteable code block containing only the fixed version of the specific erroneous segment found in the codebase."
            "If a non-imported library is required to fix the code or if any additions need to be made to the code, it must be added to the fixed code."
        ),
    )
    original_code: str = Field(
        description = "The exact, unmodified lines of code from the original source that triggered the error.",
    )

    error_severity: SEVERITY_TYPE = Field(
        description = "The criticality of the error regarding code execution, categorized as LOW, MEDIUM, HIGH, or CRITICAL."
    )
    fix_effort: EFFORT_TYPE = Field(
        description = "The difficulty and effort required to resolve the error, categorized as QUICK, BALANCED, or ADVANCED.",
    )


class Suggestion(BaseModel):
    title: str = Field(
        description = "A brief, descriptive title for this specific suggestion.",
    )
    line_range: tuple[int, int] = Field(
        description =(
            "The specific starting and ending line numbers of the code that triggered this suggestion, represented as a tuple [start_line, end_line]. "
            "IMPORTANT: You must always provide a tuple. If the suggestion applies to a single line (e.g., line 1), return it as (1, 1). "
            "If the suggestion spans multiple lines (e.g., from line 12 to 16), return it as (12, 16)."
        ),
        examples = [(1, 12), (2, 23), (3, 6)],
    )

    suggestion_reason: str = Field(
        description = "A brief explanation of the problem solved or the benefit gained by applying this suggestion.",
    )
    suggested_code: str = Field(
        description = (
            "The production-ready, copy-pasteable code block demonstrating the proposed solution. "
            "If a non-imported library is required to implement the suggestion or if any additions to the code are required, "
            "it must be added in the suggestion code."
        ),
    )
    original_code: str = Field(
        description = "The original lines of code copied verbatim from the user's snippet that triggered this suggestion.",
    )

    suggestion_priority: SEVERITY_TYPE = Field(
        description = "The criticality of the suggestion, categorized as LOW, MEDIUM, HIGH, or CRITICAL.",
    )
    suggestion_effort: EFFORT_TYPE = Field(
        description = "The difficulty and effort required the suggestion, categorized as QUICK, BALANCED, or ADVANCED.",
    )


class CodeInspectorSchema(BaseModel):
    errors: list[Error] = Field(
        description = (
            "An array of objects detailing detected bugs, including their titles, technical types, "
            "root causes, line ranges, fixing effort, severity, suggested code and recommended fixes."
        ),
    )
    suggestions: list[Suggestion] = Field(
        description = (
            "An actionable collection of structured optimization and refactoring suggestions aimed at "
            "improving the codebase's architecture, maintainability, and quality."
        ),
    )


class CodeScorerSchema(BaseModel):
    security_score: int = Field(
        description = (
            "A score from 0 to 10 evaluating the overall security and reliability of the code (10 being highly secure, 0 being highly vulnerable), "
            "The evaluation must analyze active security vulnerabilities and identify code segments that could pose security risks in the future."
        ),
    )
    cleanliness_score: int = Field(
        description = (
            "A score from 0 to 10 evaluating code cleanliness, adherence to language-specific style guides and standards "
            "(10 being pristine/highly compliant, 0 being poorly written)."
        ),
    )
    performance_score: int = Field(
        description = (
            "A score from 0 to 10 evaluating execution efficiency and performance (10 being highly optimized, 0 being highly inefficient), "
            "The evaluation must specifically focus on critical sections impacting execution speed, resource utilization, and runtime efficiency."
        ),
    )
    overall_score: int = Field(
        description = (
            "A comprehensive quality score from 0 to 10 evaluating the codebase as a whole (10 being exceptional quality, 0 being extremely poor quality). "
            "This score must aggregate the previous metrics while considering the broader architectural characteristics of the code."
        ),
    )
    scalibility_score: int = Field(
        description = (
            "A score from 0 to 10 evaluating how resilient and healthy the code will remain as the application scales, "
            "specifically focusing on its ability to handle increases in data volume, data structure complexity, and concurrent user requests."
        ),
    )
    breaking_changes_score: int = Field(
        description = (
            "A score from 0 to 10 evaluating the code's vulnerability to breaking changes, "
            "specifically measuring how likely it is to break when external dependencies, "
            "software libraries, or the programming language version are updated."
        ),
    )

    scores_reasons: str = Field(description = "A detailed breakdown providing the justification and reasoning behind each assigned score.")


class CodeProfılerSchema(BaseModel):
    summary: str = Field(
        description = "A high-level overview summarizing the functionality, core logic, and overall purpose of the entire codebase.",
    )
    lint_warnings: list[str] = Field(
        description = (
            "A list of stylistic violations, formatting issues, and non-idiomatic patterns that deviate from industry-standard style guides (e.g., PEP 8, ESLint). "
            "It highlights where the code is syntactically correct but breaks conventions regarding naming, "
            "indentation, line lengths, or unused imports, which reduces readability."
        ),
    )
    pros: list[str] = Field(
        description = "Key strengths, advantages, well-implemented features, and positive aspects of the code.",
    )
    cons: list[str] = Field(
        description = "Weaknesses, disadvantages, architectural bottlenecks, and structural downsides of the code.",
    )

class State(TypedDict):
    profiler_report: CodeProfılerSchema | None
    scorer_report: CodeScorerSchema | None
    inspector_report: CodeInspectorSchema | None
    final_report: str | None
    formatted_reports: str | None
    code: str

@dataclass 
class AnalysisReport:
    profiler_report: Optional[CodeProfılerSchema] = None
    scorer_report: Optional[CodeScorerSchema] = None
    inspector_report: Optional[CodeInspectorSchema] = None
    final_report: str = ""

@dataclass
class NodeFlag:
    worker_name: NODE_NAMES
    flag: bool = True # true if node is started, False if node is completed.