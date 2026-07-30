from langchain_community.document_loaders import TextLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import dotenv_values, get_key, set_key
from .state import AnalysisReport, NodeFlag
from typing import Optional, Callable, Any
from IPython.display import display, Image
from platformdirs import user_cache_dir
from .graph import get_analyzer_graph
from pathlib import Path
import os

CACHED_ENV = Path(user_cache_dir(), "code-analyzer", ".env")
GOOGLE_KEY_NAME = "GOOGLE_API_KEY"

class APIKeyNotFoundError(Exception):
    """API key was not found."""

class CodeAnalyzer:
    def __init__(self, model_name: str, api_key: str | None = None, **GoogleGenAIKwargs):
        """
        Performs comprehensive analysis of code snippets and files, 
        detecting errors and metrics while generating recommendations and detailed reports.

        To use this class, you must set the GOOGLE_API_KEY environment variable in your .env file or you must set your permanent key with 'set_cached_key' method.

        Args:
            model_name(str):
                The name of the Google Generative AI model to use.
            GoogleGenAIKwargs:
                Configuration parameters passed as keyword arguments to the ChatGoogleGenerativeAI constructor.
            api_key(str):
                The API key for Google Generative AI services. 
                This parameter can be omitted if a valid key is already detected in the current or cached .env file. 
                Use set_cache_key() to update the cached key.

        Example:
            >>> analyzer = CodeAnalyzer(model_name = "gemini-2.5-flash-lite", api_key = your_api_key)

            Analyze a local file;
            >>> result = analyzer.analyze_from_file("main.py")

            Analyze a code string (synchronous);
            >>> result = analyzer.analyze('print("Hello, word")')

            Analyze a code string (asynchronous);
            >>> result = await analyzer.async_analyze('print("Hello, word")')

        """

        model_kwargs = {"model": model_name, "max_retries": 2, "timeout": 60}

        env_api_key = self.get_env_key()
        model_api_key = api_key if api_key else env_api_key

        if model_api_key:
            model_kwargs["api_key"] = model_api_key
        else:
            raise APIKeyNotFoundError(
                "The Google API key was not found in the current or cached .env file. Please define the api_key parameter "
                "or manually add the API key to your current .env file or add it to cached .env file using the 'set_cached_key' method."
            )

        llm = ChatGoogleGenerativeAI(**model_kwargs, **GoogleGenAIKwargs)
        self._graph = get_analyzer_graph(llm)


    def analyze(
        self, 
        code: str, 
        callback: Optional[Callable[[AnalysisReport | NodeFlag], None]] = None
    ) -> Optional[dict[str, Any] | Any]:
        
        """
        Start the code analyze process.

        Args:
            code(str):
                The source code subject to analysis.
            callback(Optional[Callable[[AnalysisReport | NodeFlag], None]]):
                The function that receives feedback from graph nodes during the analysis process.

        Returns:
            If the callback is not defined, it returns the graph's state as a dictionary otherwise it returns None.
        """
        
        if not code:
            raise ValueError("The 'code' parameter must be defined.")
        
        if not isinstance(code, str):
            raise ValueError("The 'code' parameter must be a str object")
        
        if not isinstance(callback, Callable) and callback is not None:
            raise ValueError("The 'callback' paramater must be a callable object or None")
        
        state = self._graph.invoke(
            {"code": code},
            config = {
                "configurable": {"callback": callback}
            }
        )

        if not callback:
            return state
    
    def analyze_from_file(
        self, 
        file_name_or_path: str | Path, 
        callback: Optional[Callable[[AnalysisReport | NodeFlag], None]] = None
    ) -> Optional[dict[str, Any] | Any]:
        """
        Start the code analysis process from the file.

        Args:
            file_name(str):
                The path or name of the file to be processed by the analyzer.
            callback(Optional[Callable[[AnalysisReport | NodeFlag], None]]):
                The function that receives feedback from graph nodes during the analysis process.

        Returns:
            If the callback is not defined, it returns the graph's state as a dictionary otherwise it returns None.
        """

        if not file_name_or_path:
            raise ValueError("The 'file_name' parameter must be defined.")
        
        if not isinstance(file_name_or_path, (str, Path)):
            raise ValueError("The 'file_name' parameter must be a string or Path object containing the file path.")
        
        if not isinstance(callback, Callable) and callback is not None:
            raise ValueError("The 'callback' paramater must be a callable object or None")
        
        path = Path(file_name_or_path)
        if not path.exists():
            raise FileNotFoundError(f"'{file_name_or_path}' file is not exist.")
        
        loader = TextLoader(path, autodetect_encoding = True)
        documents = loader.load()

        code = "".join([d.page_content for d in documents])
        if code:
            state = self.analyze(code, callback)
            return state

    async def async_analyze(
        self, 
        code: str, 
        callback: Optional[Callable[[AnalysisReport | NodeFlag], None]] = None
    ) -> Optional[dict[str, Any] | Any]:
        
        """
        Start the asynchronous code analysis process.

        Args:
            code(str):
                The source code subject to analysis.
            callback(Optional[Callable[[AnalysisReport | NodeFlag], None]]):
                The function that receives feedback from graph nodes during the analysis process.

        Returns:
            If the callback is not defined, it returns the graph's state as a dictionary otherwise it returns None.
        
        """
        
        if not code:
            raise ValueError("The 'code' parameter must be defined.")

        if not isinstance(code, str):
            raise ValueError("The 'code' parameter must be a str object")

        if not isinstance(callback, Callable) and callback is not None:
            raise ValueError("The 'callback' paramater must be a callable object or None")
        
        state = await self._graph.ainvoke(
            {"code": code},
            config = {
                "configurable": {"callback": callback}
            }
        )

        if not callback:
            return state
        
    def display_graph_image(self) -> None:
        """
        
        display the graph image.
        
        """
        display(Image(self._graph.get_graph().draw_mermaid_png()))

    def get_env_key(self) -> Optional[str]:
        """
        
        Checks environment variables and returns the API key if available.
        
        """
        current_dotenv = Path(Path.cwd(), ".env")
        env_api_key = None

        if current_dotenv.exists():
            env_api_key = dotenv_values(current_dotenv).get("GOOGLE_API_KEY")
        else:
            if CACHED_ENV.exists():
                env_api_key = dotenv_values(CACHED_ENV).get("GOOGLE_API_KEY")
            else:
                CACHED_ENV.parent.mkdir(parents = True, exist_ok = True)
                CACHED_ENV.touch(exist_ok = True)
        
        if not env_api_key:
            env_api_key = os.getenv("GOOGLE_API_KEY")
            if env_api_key:
                self.set_cached_key(env_api_key)

        return env_api_key

    @staticmethod
    def get_cached_key() -> Optional[str]:
        """
        
        Get the cached Google API key.
        
        """

        if CACHED_ENV.exists():
            result = get_key(dotenv_path = CACHED_ENV, key_to_get = GOOGLE_KEY_NAME)
            if not result:
                raise APIKeyNotFoundError(
                    "The Google API key was not found in the cached .env file. Please use to 'set_cached_key' method."
                )
            else: return result

        else:
            CACHED_ENV.parent.mkdir(parents = True, exist_ok = True)
            CACHED_ENV.touch(exist_ok = True)

            raise APIKeyNotFoundError("The Google API key was not found in the cached .env file. Please use to 'set_cached_key' method.")
    
    @staticmethod
    def set_cached_key(google_api_key: str):
        """
        
        Set the cached Google API key.
        
        """
        if not CACHED_ENV.exists():
            CACHED_ENV.parent.mkdir(parents = True, exist_ok = True)
            CACHED_ENV.touch(exist_ok = True)

        set_key(dotenv_path = CACHED_ENV, key_to_set = GOOGLE_KEY_NAME, value_to_set = google_api_key)