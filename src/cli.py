from concurrent.futures import ThreadPoolExecutor, Future
from .analyzer import CodeAnalyzer, APIKeyNotFoundError
from .state import AnalysisReport, NodeFlag
from .formatter import report_formatter
from typing import Optional, Literal
from rich.markdown import Markdown
from rich.console import Console
from rich.text import Text
import subprocess
import argparse
import queue
import time
import sys
import os

class ConsoleManager:
    thread_executor = ThreadPoolExecutor()
    print_queue = queue.Queue()
    console = Console()
    _is_continue = False

    @classmethod
    def process_queue(cls, graph_worker: Future):
        while cls._is_continue:
            if graph_worker.done() and graph_worker.exception():
                break
            try:
                args_dict = cls.print_queue.get(timeout = 0.1)
            except queue.Empty:
                if graph_worker.done():
                    break
                continue

            if isinstance(args_dict, dict):
                printer_type = args_dict.pop("printer_type")

                if printer_type == "text":
                    cls.text_printer(**args_dict)

                elif printer_type == "markdown":
                    cls.markdown_printer(**args_dict)

                else: continue


    @classmethod
    def add_to_queue(
        cls,
        content: str = "",
        *,
        printer_type: Literal["text", "markdown"] = "text",
        display_style: Optional[str] = None,
        add_space: Optional[bool] = None,
        sleep: Optional[float] = None,
    ) -> None:
        args_dict = {"printer_type": printer_type}

        if display_style: args_dict["display_style"] = display_style
        if add_space: args_dict["add_space"] = add_space
        if content: args_dict["content"] = content
        if sleep: args_dict["sleep"] = sleep

        cls.print_queue.put(args_dict)

    @classmethod
    def markdown_printer(
        cls, 
        content: str = "",
        *,
        add_space: bool = False,
        sleep: Optional[float] = None,
    ) -> None:
        
        cls.console.print(Markdown(content))

        if add_space and isinstance(add_space, bool):
            cls.console.print()

        if sleep and isinstance(sleep, (float, int)):
            sleep_count = 0
            while sleep_count < sleep:
                if not cls._is_continue:
                    return
                time.sleep(0.1)
                sleep_count += 0.1


    @classmethod
    def text_printer(
        cls, 
        content: str = "",
        *,
        display_style: str = "bold white",
        add_space: bool = False,
        sleep: Optional[float] = None,
    ) -> None:
        
        cls.console.print(Text(content, style = display_style))

        if add_space and isinstance(add_space, bool):
            cls.console.print()

        if sleep and isinstance(sleep, (float, int)):
            sleep_count = 0
            while sleep_count < sleep:
                if not cls._is_continue:
                    return
                time.sleep(0.1)
                sleep_count += 0.1


    @classmethod
    def start_process(cls) -> None:
        cls.console.show_cursor(False)
        cls._is_continue = True

    @classmethod
    def close_process(cls) -> None:
        cls._is_continue = False
        cls.thread_executor.shutdown(wait = False, cancel_futures = True)
        while not cls.print_queue.empty():
            cls.print_queue.get_nowait()
        cls.console.show_cursor(True)

    @classmethod
    def clear_console(cls) -> None:
        if os.name == "nt": cmd = "cls"
        else: cmd = "clear"

        sys.stdout.flush()
        subprocess.run(cmd, check = True) 

def cli_callback(data: AnalysisReport | NodeFlag):

    if isinstance(data, NodeFlag):
        start, end = "is started", "is completed"

        ConsoleManager.add_to_queue(
            f"{data.worker_name} {start if data.flag else end}",
            printer_type = "text",
            display_style = "bold green",  
            sleep = 0.5
        )

                     
    if isinstance(data, AnalysisReport):
        base_text_args = {"display_style": "bold white"}

        base_text_args["sleep"] = 2.0
        base_text_args["printer_type"] = "text"
        base_text_args["add_space"] = True

        if data.inspector_report:
            inspector_text = report_formatter(inspector_report = data.inspector_report)
            ConsoleManager.add_to_queue(inspector_text, **base_text_args)

        if data.profiler_report:
            profiler_text = report_formatter(profiler_report = data.profiler_report)
            ConsoleManager.add_to_queue(profiler_text, **base_text_args)

        if data.scorer_report:
            scorer_text = report_formatter(scorer_report = data.scorer_report)
            ConsoleManager.add_to_queue(scorer_text, **base_text_args)

        if data.final_report:
            ConsoleManager.add_to_queue(data.final_report, printer_type = "markdown")


def configure_the_key(args):
    if args.set_key or args.get_key:
        set_key = args.set_key
        get_key = args.get_key

        try:
            if set_key: 
                CodeAnalyzer.set_cached_key(set_key)
                ConsoleManager.console.print(f"Configuration of API key completed successfully.", style = "bold green")
                sys.exit(0)

            elif get_key:
                result = CodeAnalyzer.get_cached_key()
                ConsoleManager.console.print(f"[bold green]API key found successfully[/bold green]: [bold blue]{result}[/bold blue]")
                sys.exit(0)

            else: 
                ConsoleManager.console.print("[bold yellow]The parameter or parameters are missing, please define the parameters exactly.[/bold yellow]")
                sys.exit(1)

        except APIKeyNotFoundError:
            ConsoleManager.console.print(f"[bold yellow]The Google API key was not found in the cached .env file. Please use to '--set-key' and save your key permanently.[/bold yellow]")
            sys.exit(1)       

        except Exception as e:
            ConsoleManager.console.print(f"[bold red]An error occurred during the API key configuration process[/bold red]: {str(e)}")
            sys.exit(1)
            

def start_analyze(args):
    try:
        analyzer = CodeAnalyzer(model_name = args.model, api_key = args.api_key)
    except APIKeyNotFoundError:
        msg = (
            "API key not found in current or cached .env files. Please launch code-analyzer with the '--api-key' "
            "flag or save your key permanently using 'code-analyzer config --set-key your_api_key'"
        )
        ConsoleManager.clear_console()
        ConsoleManager.console.print(msg, style = "bold yellow")
        sys.exit(1)

    except Exception as e:
        ConsoleManager.clear_console()
        ConsoleManager.console.print(f"[bold red]An error occurred during the model initialization process[/bold red]: {str(e)}")
        sys.exit(1)

    if args.code or args.path:
        path, code = args.path, args.code

        if code: func, func_input = analyzer.analyze, code
        if path: func, func_input = analyzer.analyze_from_file, path

        try:
            ConsoleManager.start_process()

            graph_worker = ConsoleManager.thread_executor.submit(func, func_input, cli_callback)
            queue_worker = ConsoleManager.thread_executor.submit(ConsoleManager.process_queue, graph_worker)

            queue_worker.result()
            graph_worker.result()

            ConsoleManager.close_process()
            sys.exit(0)

        except KeyboardInterrupt:
            ConsoleManager.close_process()
            ConsoleManager.clear_console()
            ConsoleManager.console.print(f"[bold yellow]The program was stopped by the user.[/bold yellow]")
            sys.exit(1)

        except Exception as e:
            ConsoleManager.close_process()
            ConsoleManager.clear_console()
            ConsoleManager.console.print(f"[bold red]An error occurred during analysis[/bold red]: {str(e)}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description = "code-analyzer: A code analyzer cli tool powered by langgraph workflows",
        formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )

    subparsers = parser.add_subparsers(
        dest = "command",
        required = True,
        help = "Select the operational mode to execute"
    )

    config_parser = subparsers.add_parser(
        "config",
        help = "Configure operational keys and environment variables persistently."
    )

    config_group = config_parser.add_mutually_exclusive_group(required = True)

    config_group.add_argument(
        "--set-key",
        type = str,
        help = "Sets or updates the API key for global use. The key is stored locally and will be used automatically in future sessions."
    )

    config_group.add_argument(
        "--get-key",
        action = "store_true",
        help = "Get the saved API key, if available"
    )

    config_parser.set_defaults(func = configure_the_key)

    run_parser = subparsers.add_parser(
        "run",
        help = "Start the code analysis pipeline."
    )

    run_group = run_parser.add_mutually_exclusive_group(required = True)
    run_group.add_argument(
        "--code",
        type = str,
        help = "The raw code snippet string to be analyzed directly from the terminal."
    )

    run_group.add_argument(
        "--path",
        type = str,
        help = "The local file path pointing to the code file you want to analyze."
    )

    run_parser.add_argument(
        "--model",
        type = str,
        default = "gemini-2.5-flash-lite",
        help = "The Google Generative AI model name to be used for analysis."
    )

    run_parser.add_argument(
        "--api-key",
        type = str,
        default = None,
        help = "Optional runtime API key bypass string to avoid persisting configuration."
    )

    run_parser.set_defaults(func = start_analyze)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()