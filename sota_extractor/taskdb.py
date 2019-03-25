import json
import csv
from typing import Dict, List


class Link:
    def __init__(self, d: Dict):
        """Make a new Link to a URL from the dictionary of values.

        Args:
            d: A dictionary with the data (from the JSON).
        """

        self.title = ""
        self.url = ""

        if "title" in d:
            self.title = d["title"]

        if "url" in d:
            self.url = d["url"]

    def to_dict(self) -> Dict:
        return {"title": self.title, "url": self.url}


class SotaRow:
    def __init__(self, d: Dict):
        """Row of the SOTA table.

        Args:
            d: A dictionary with the data (from the JSON).
        """

        self.model_name = d["model_name"]
        self.paper_title = ""
        self.paper_url = ""
        self.paper_date = None

        if "paper_title" in d:
            self.paper_title = d["paper_title"]

        if "paper_url" in d:
            self.paper_url = d["paper_url"]

        if "paper_date" in d:
            self.paper_date = d["paper_date"]

        self.code_links = []
        self.model_links = []

        if "code_links" in d:
            for code_d in d["code_links"]:
                if code_d:
                    self.code_links.append(Link(code_d))

        if "model_links" in d:
            for model_d in d["model_links"]:
                if model_d:
                    self.model_links.append(Link(model_d))

        self.metrics = d["metrics"]

    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "paper_title": self.paper_title,
            "paper_url": self.paper_url,
            "paper_date": self.paper_date,
            "code_links": [l.to_dict() for l in self.code_links],
            "model_links": [l.to_dict() for l in self.model_links],
            "metrics": self.metrics,
        }


class Dataset:
    def __init__(self, d: Dict, parent=None):
        """Make a new Dataset instance from a dictionary of values.

        Args:
            d: A dictionary with the data (from the JSON).
            parent: The parent dataset if present, i.e if the dataset is a
                subdataset.
        """
        if "subdataset" in d:
            self.dataset = d["subdataset"]
        else:
            self.dataset = d["dataset"]
        self.description = ""
        if "description" in d:
            self.description = d["description"]

        self.parent = parent

        self.sota_metrics = []
        self.sota_rows = []

        if "sota" in d:
            if "metrics" in d["sota"]:
                self.sota_metrics = d["sota"]["metrics"]
            if "rows" in d["sota"]:
                for sota_row_d in d["sota"]["rows"]:
                    if sota_row_d:
                        self.sota_rows.append(SotaRow(sota_row_d))

        self.subdatasets = []
        if "subdatasets" in d:
            for subd_d in d["subdatasets"]:
                if subd_d:
                    self.subdatasets.append(Dataset(subd_d, parent=self))

        self.dataset_links = []
        if "dataset_links" in d:
            for link_d in d["dataset_links"]:
                if link_d:
                    self.dataset_links.append(Link(link_d))

        self.dataset_citations = []
        if "dataset_citations" in d:
            for link_d in d["dataset_citations"]:
                if link_d:
                    self.dataset_links.append(Link(link_d))

    def to_dict(self) -> Dict:
        o = {}
        if self.parent:
            o["subdataset"] = self.dataset
        else:
            o["dataset"] = self.dataset

        o["description"] = self.description
        if self.sota_metrics:
            o["sota"] = {
                "metrics": self.sota_metrics,
                "rows": [m.to_dict() for m in self.sota_rows],
            }

        if self.subdatasets:
            o["subdatasets"] = [d.to_dict() for d in self.subdatasets]

        o["dataset_links"] = [l.to_dict() for l in self.dataset_links]
        o["dataset_citations"] = [l.to_dict() for l in self.dataset_citations]

        return o


class Task:
    def __init__(self, d: Dict, parent=None):
        """Make a new Task from a dictionary of values.

        Args:
            d: a dictionary with all the data (from the JSON).
            parent: The parent Task (if any).
        """
        self.task = d["task"]
        self.description = ""
        if "description" in d:
            self.description = d["description"]
        self.parent = parent

        self.categories = []
        if "categories" in d:
            self.categories = d["categories"]

        self.datasets = []
        if "datasets" in d:
            for dataset_d in d["datasets"]:
                if dataset_d:
                    self.datasets.append(Dataset(dataset_d))

        self.subtasks = []
        if "subtasks" in d:
            for subt_d in d["subtasks"]:
                if subt_d:
                    self.subtasks.append(Task(subt_d, parent=self))

        self.synonyms = []
        self.source_link = None
        if "source_link" in d:
            self.source_link = Link(d["source_link"])

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "description": self.description,
            "categories": self.categories,
            "datasets": [d.to_dict() for d in self.datasets],
            "subtasks": [t.to_dict() for t in self.subtasks],
            "synonyms": self.synonyms,
            "source_link": self.source_link.to_dict()
            if self.source_link
            else None,
        }


class TaskDb:
    tasks = {}

    @staticmethod
    def get_task(name: str):
        """Get a task or subtask by name."""
        if name in TaskDb.tasks:
            return TaskDb.tasks[name]
        else:
            for t in TaskDb.tasks.values():
                for subtask in t.subtasks:
                    if subtask.task == name:
                        return subtask
        return None

    @staticmethod
    def add_task(name: str, task: Task):
        """Add a top-level task by name."""
        TaskDb.tasks[name] = task

    @staticmethod
    def load_tasks(json_files: List[str]):
        """Load tasks from a list of paths to JSON Files."""
        for json_file in json_files:
            with open(json_file, "r") as f:
                task_list = json.load(f)
                for t in task_list:
                    TaskDb.add_task(t["task"], Task(t))

    @staticmethod
    def load_synonyms(csv_files: List[str]):
        """Load task synonyms from input files."""
        for csv_file in csv_files:
            with open(csv_file, newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    task = TaskDb.get_task(row[0])
                    if task is not None:
                        task.synonyms.append(row[1])

    @staticmethod
    def tasks_with_sota() -> List[Task]:
        """Extract all tasks with SOTA tables.

        This includes both the top-level and sub-tasks.
        """
        sota_tasks = []

        for task in TaskDb.tasks.values():
            find_sota_tasks(task, sota_tasks)

        return sota_tasks

    @staticmethod
    def datasets_with_sota() -> List[Dataset]:
        """Extract all datasets with SOTA tables.

        This includes both the top-level and sub-tasks.
        """

        sota_datasets = []

        for task in TaskDb.tasks.values():
            find_sota_datasets(task, sota_datasets)

        return sota_datasets

    @staticmethod
    def export() -> List[Dict]:
        """Export the whole of TaskDB into a list of tasks in Dict format."""
        return [task.to_dict() for task in TaskDb.tasks.values()]

    @staticmethod
    def export_to_json(json_filename: str):
        """Export the whole of TaskDB into a JSON file."""
        with open(json_filename, "w") as f:
            json.dump(TaskDb.export(), f, indent=2)


def find_sota_tasks(task: Task, out: List):
    """Get all the tasks with a SOTA table.

    These tasks will be added into the "out" output list.
    """
    # check if the dataset has sota tables
    add = False
    for d in task.datasets:
        if d.sota_rows:
            add = True

        for sd in d.subdatasets:
            if sd.sota_rows:
                add = True

    if add:
        out.append(task)

    for subtask in task.subtasks:
        find_sota_tasks(subtask, out)


def find_sota_datasets(task: Task, out: List):
    """Get all the datasets with a SOTA table.

    These datasets will be added into the "out" output list.
    """

    # check if the dataset has sota tables
    add = False
    for d in task.datasets:
        if d.sota_rows:
            add = True

        for sd in d.subdatasets:
            if sd.sota_rows:
                add = True

        if add:
            out.append(d)

    for subtask in task.subtasks:
        find_sota_datasets(subtask, out)
