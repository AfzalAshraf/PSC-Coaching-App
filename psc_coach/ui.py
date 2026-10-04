"""Offline-first Tkinter interface for the Kerala PSC Coach desktop app."""

from __future__ import annotations

import csv
import json
import random
import time
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from typing import Any

from .build_info import APP_VERSION
from .catalog import CURRENT_AFFAIRS_SOURCES, DOMAIN_LABELS, TRACKS, track_domain_ids
from .learning import (
    NotEnoughQuestionsError,
    daily_plan,
    due_flashcards,
    select_questions,
    set_task_completion,
    task_completion,
    update_after_session,
    schedule_flashcard,
    weak_domains,
)
from .questions import QuestionPackError, build_question_pool, load_question_pack
from .storage import ProfileStore, default_profile

APP_TITLE = "Kerala PSC Coach"
LATEST_RELEASE_URL = "https://github.com/AfzalAshraf/PSC-Coaching-App/releases/latest"

COLORS = {
    "bg": "#f3f6f4",
    "panel": "#ffffff",
    "panel_alt": "#eaf2ee",
    "ink": "#182c25",
    "muted": "#687a72",
    "muted_light": "#91a198",
    "border": "#dbe5df",
    "nav": "#102a24",
    "nav_hover": "#1c4036",
    "accent": "#087f5b",
    "accent_dark": "#056448",
    "accent_light": "#e0f3eb",
    "blue": "#2f69a8",
    "blue_light": "#e8f1fb",
    "gold": "#ae7600",
    "gold_light": "#fff5d9",
    "red": "#b64747",
    "red_light": "#fff0ef",
    "purple": "#7054a3",
    "purple_light": "#f1edfa",
    "white": "#ffffff",
}

FONT = "Segoe UI"


def _minutes(seconds: int | float) -> str:
    seconds = max(0, int(seconds))
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}:{remainder:02d}"


def _percent(value: float) -> str:
    return f"{value:.0f}%" if float(value).is_integer() else f"{value:.1f}%"


class ScrollFrame(ttk.Frame):
    """A lightweight vertically scrollable frame built with Tkinter Canvas."""

    def __init__(self, master: tk.Misc, *, background: str = COLORS["bg"]):
        super().__init__(master, style="Page.TFrame")
        self.canvas = tk.Canvas(self, background=background, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, background=background)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.canvas.bind("<Button-4>", lambda _event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda _event: self.canvas.yview_scroll(1, "units"))

    def _update_scroll_region(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window, width=max(1, event.width - 4))

    def _mousewheel(self, event: tk.Event) -> None:
        try:
            if self.winfo_exists() and self.winfo_ismapped():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass


class PSCCoachApp(tk.Tk):
    """Main application window; all learning data stays on the user's device."""

    NAV_ITEMS = (
        ("home", "Overview"),
        ("practice", "Practice & Mocks"),
        ("flashcards", "Flashcards"),
        ("progress", "My Progress"),
        ("settings", "Library & Settings"),
    )

    def __init__(self, store: ProfileStore | None = None):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1260x850")
        self.minsize(1020, 680)
        self.configure(background=COLORS["bg"])
        self.store = store or ProfileStore()
        self.profile = self.store.load()
        self.current_track = self.profile["settings"].get("track", "10th")
        self.question_pool = build_question_pool(self.profile.get("custom_questions", []))
        self.current_page = "home"
        self.session: dict[str, Any] | None = None
        self.last_result: dict[str, Any] | None = None
        self._timer_job: str | None = None
        self._finishing = False
        self._page_host: ttk.Frame | None = None
        self._nav_buttons: dict[str, tk.Button] = {}
        self._configure_styles()
        self._build_shell()
        self.show_page("home")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.store.load_warning:
            self.after(400, lambda: messagebox.showwarning(APP_TITLE, self.store.load_warning))
        elif self.store.migrated:
            self.after(400, lambda: messagebox.showinfo(
                APP_TITLE,
                "Your saved scores and flashcards from the previous version were brought into this profile.",
            ))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Page.TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["ink"], font=(FONT, 10))
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=(FONT, 9))
        style.configure("TButton", font=(FONT, 10), padding=(12, 8))
        style.configure(
            "Accent.TButton", background=COLORS["accent"], foreground=COLORS["white"],
            borderwidth=0, font=(FONT, 10, "bold"), padding=(16, 10),
        )
        style.map("Accent.TButton", background=[("active", COLORS["accent_dark"]), ("disabled", "#a9c9bb")])
        style.configure(
            "Soft.TButton", background=COLORS["panel_alt"], foreground=COLORS["ink"],
            borderwidth=0, padding=(12, 8),
        )
        style.map("Soft.TButton", background=[("active", "#dce9e2")])
        style.configure(
            "Danger.TButton", background=COLORS["red_light"], foreground=COLORS["red"],
            borderwidth=0, padding=(12, 8),
        )
        style.configure("TEntry", padding=7, fieldbackground=COLORS["white"])
        style.configure("TCombobox", padding=7, fieldbackground=COLORS["white"])
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["white"])])
        style.configure("Horizontal.TProgressbar", troughcolor=COLORS["panel_alt"], background=COLORS["accent"])
        style.configure("Treeview", font=(FONT, 9), rowheight=30, background=COLORS["white"], fieldbackground=COLORS["white"])
        style.configure("Treeview.Heading", font=(FONT, 9, "bold"), background=COLORS["panel_alt"])

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, background=COLORS["nav"], width=224)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, background=COLORS["nav"])
        brand.pack(fill="x", padx=22, pady=(27, 29))
        tk.Label(brand, text="PSC", font=(FONT, 11, "bold"), fg=COLORS["nav"], bg="#8fe1be", padx=8, pady=5).pack(side="left")
        tk.Label(brand, text="  COACH", font=(FONT, 16, "bold"), fg=COLORS["white"], bg=COLORS["nav"]).pack(side="left")
        tk.Label(
            self.sidebar,
            text="YOUR PREPARATION",
            font=(FONT, 8, "bold"),
            fg="#82a397",
            bg=COLORS["nav"],
            anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 10))

        for page, label in self.NAV_ITEMS:
            button = tk.Button(
                self.sidebar,
                text=f"  {label}",
                command=lambda name=page: self.show_page(name),
                anchor="w",
                relief="flat",
                bd=0,
                padx=16,
                pady=12,
                font=(FONT, 10, "bold"),
                fg="#c7d9d1",
                bg=COLORS["nav"],
                activeforeground=COLORS["white"],
                activebackground=COLORS["nav_hover"],
                cursor="hand2",
            )
            button.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[page] = button

        spacer = tk.Frame(self.sidebar, background=COLORS["nav"])
        spacer.pack(fill="both", expand=True)
        tk.Frame(self.sidebar, height=1, bg="#315148").pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(
            self.sidebar,
            text="Independent study tool\nNot affiliated with Kerala PSC",
            justify="left",
            font=(FONT, 8),
            fg="#91a99f",
            bg=COLORS["nav"],
        ).pack(anchor="w", padx=22, pady=(0, 7))
        tk.Label(self.sidebar, text=f"Version {APP_VERSION}", font=(FONT, 8), fg="#70877e", bg=COLORS["nav"]).pack(anchor="w", padx=22, pady=(0, 18))

        self.work_area = tk.Frame(self, background=COLORS["bg"])
        self.work_area.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(self.work_area, background=COLORS["white"], height=64, highlightbackground=COLORS["border"], highlightthickness=1)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.page_title_var = tk.StringVar(value="Overview")
        tk.Label(topbar, textvariable=self.page_title_var, font=(FONT, 13, "bold"), fg=COLORS["ink"], bg=COLORS["white"]).pack(side="left", padx=25)
        self.local_tag = tk.Label(
            topbar,
            text="OFFLINE-FIRST  ·  YOUR DATA STAYS LOCAL",
            font=(FONT, 8, "bold"),
            fg=COLORS["accent"],
            bg=COLORS["accent_light"],
            padx=10,
            pady=6,
        )
        self.local_tag.pack(side="right", padx=23)
        self._page_host = ttk.Frame(self.work_area)
        self._page_host.pack(fill="both", expand=True)

    def _save_profile(self, *, quiet: bool = False) -> bool:
        try:
            self.store.save(self.profile)
            return True
        except OSError as exc:
            if not quiet:
                messagebox.showerror(APP_TITLE, f"Your progress could not be saved.\n\n{exc}")
            return False

    def _clear_page(self) -> None:
        assert self._page_host is not None
        for child in self._page_host.winfo_children():
            child.destroy()

    def _new_scroll_page(self) -> tk.Frame:
        self._clear_page()
        assert self._page_host is not None
        scroll = ScrollFrame(self._page_host)
        scroll.pack(fill="both", expand=True)
        return scroll.inner

    def _card(self, parent: tk.Misc, *, background: str = COLORS["panel"], padding: int = 18) -> tk.Frame:
        outer = tk.Frame(parent, bg=background, highlightbackground=COLORS["border"], highlightthickness=1)
        inner = tk.Frame(outer, bg=background)
        inner.pack(fill="both", expand=True, padx=padding, pady=padding)
        outer.content = inner  # type: ignore[attr-defined]
        return outer

    def _label(
        self,
        parent: tk.Misc,
        text: str,
        *,
        size: int = 10,
        bold: bool = False,
        color: str = COLORS["ink"],
        background: str = COLORS["bg"],
        wrap: int = 0,
        justify: str = "left",
        **kwargs: Any,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            font=(FONT, size, "bold" if bold else "normal"),
            fg=color,
            bg=background,
            wraplength=wrap,
            justify=justify,
            **kwargs,
        )

    def _button(self, parent: tk.Misc, text: str, command, *, primary: bool = False, compact: bool = False, **kwargs: Any) -> ttk.Button:
        style = "Accent.TButton" if primary else "Soft.TButton"
        if compact:
            kwargs.setdefault("padding", (9, 6))
        return ttk.Button(parent, text=text, command=command, style=style, **kwargs)

    def _heading(self, parent: tk.Misc, title: str, subtitle: str = "") -> None:
        # A dedicated header row keeps page-level geometry on grid consistently.
        header = tk.Frame(parent, bg=COLORS["bg"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(4, 15))
        header.grid_columnconfigure(0, weight=1)
        self._label(header, title, size=22, bold=True).pack(anchor="w", pady=(0, 2))
        if subtitle:
            self._label(header, subtitle, size=10, color=COLORS["muted"], wrap=840).pack(anchor="w")

    def show_page(self, page: str) -> None:
        if page not in {item[0] for item in self.NAV_ITEMS} and page not in {"quiz", "results"}:
            page = "home"
        if self.current_page == "quiz" and page != "quiz":
            self._cancel_timer()
        self.current_page = page
        labels = dict(self.NAV_ITEMS)
        self.page_title_var.set({"quiz": "Study Session", "results": "Session Review"}.get(page, labels.get(page, APP_TITLE)))
        active_nav = page if page in self._nav_buttons else "practice"
        for key, button in self._nav_buttons.items():
            button.configure(
                bg=COLORS["nav_hover"] if key == active_nav else COLORS["nav"],
                fg=COLORS["white"] if key == active_nav else "#c7d9d1",
            )
        renderers = {
            "home": self._render_home,
            "practice": self._render_practice,
            "flashcards": self._render_flashcards,
            "progress": self._render_progress,
            "settings": self._render_settings,
            "quiz": self._render_quiz,
            "results": self._render_results,
        }
        renderers[page]()

    def _track_selector(self, parent: tk.Misc, *, width: int = 28) -> ttk.Combobox:
        names = [track.name for track in TRACKS.values()]
        label_to_id = {track.name: track.id for track in TRACKS.values()}
        variable = tk.StringVar(value=TRACKS[self.current_track].name)
        selector = ttk.Combobox(parent, textvariable=variable, values=names, state="readonly", width=width)
        selector.bind("<<ComboboxSelected>>", lambda _event: self._change_track(label_to_id[variable.get()]))
        return selector

    def _change_track(self, track_id: str) -> None:
        if track_id not in TRACKS:
            return
        self.current_track = track_id
        self.profile["settings"]["track"] = track_id
        self._save_profile(quiet=True)
        if self.current_page in {"home", "practice"}:
            self.show_page(self.current_page)

    def _render_home(self) -> None:
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)
        stats = self.profile["stats"]
        settings = self.profile["settings"]
        total = stats.get("questions", 0)
        accuracy = 100.0 * stats.get("correct", 0) / total if total else 0.0
        due = len(due_flashcards(self.profile))
        track = TRACKS[self.current_track]
        self._heading(page, "A smarter path to your next PSC exam", "Study by syllabus, practise under pressure, and turn each mistake into a planned review.")

        hero = tk.Frame(page, bg=COLORS["nav"], padx=23, pady=21)
        hero.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        hero.grid_columnconfigure(0, weight=1)
        left = tk.Frame(hero, bg=COLORS["nav"])
        left.grid(row=0, column=0, sticky="w")
        self._label(left, f"CURRENT TRACK  ·  {track.short_name.upper()}", size=8, bold=True, color="#9cd9bf", background=COLORS["nav"]).pack(anchor="w")
        self._label(left, track.description, size=13, bold=True, color=COLORS["white"], background=COLORS["nav"], wrap=650).pack(anchor="w", pady=(7, 0))
        right = tk.Frame(hero, bg=COLORS["nav"])
        right.grid(row=0, column=1, sticky="e", padx=(20, 0))
        self._button(right, "Start a 10-question practice", lambda: self._start_session(count=10, mode="practice"), primary=True).pack(anchor="e", pady=(0, 7))
        self._button(right, "Build a timed mock", lambda: self.show_page("practice"), compact=True).pack(anchor="e")

        track_row = tk.Frame(page, bg=COLORS["bg"])
        track_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        self._label(track_row, "Prepare for", size=9, bold=True).pack(side="left", padx=(0, 10))
        self._track_selector(track_row, width=34).pack(side="left")
        self._label(track_row, "Mark splits are syllabus guides. Check your post notification for final details.", size=9, color=COLORS["muted"]).pack(side="left", padx=12)

        metric_values = [
            ("AVERAGE ACCURACY", _percent(accuracy), "Across all saved attempts", COLORS["accent"]),
            ("QUESTIONS SOLVED", f"{total:,}", f"{stats.get('sessions', 0)} practice sessions", COLORS["blue"]),
            ("STUDY STREAK", f"{stats.get('streak', 0)} days", "Consecutive active study days", COLORS["gold"]),
            ("CARDS DUE", str(due), "Recall practice ready now", COLORS["purple"]),
        ]
        metric_frame = tk.Frame(page, bg=COLORS["bg"])
        metric_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        for column in range(4):
            metric_frame.grid_columnconfigure(column, weight=1, uniform="metric")
        for column, (title, value, detail, color) in enumerate(metric_values):
            card = self._card(metric_frame, padding=15)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0 if column == 3 else 6))
            content = card.content  # type: ignore[attr-defined]
            self._label(content, title, size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")
            self._label(content, value, size=22, bold=True, color=color, background=COLORS["panel"]).pack(anchor="w", pady=(8, 2))
            self._label(content, detail, size=8, color=COLORS["muted"], background=COLORS["panel"], wrap=190).pack(anchor="w")

        plan_card = self._card(page, padding=18)
        plan_card.grid(row=4, column=0, sticky="nsew", padx=(0, 7), pady=(0, 16))
        plan = daily_plan(self.profile, self.current_track)
        checks = task_completion(self.profile)
        plan_content = plan_card.content  # type: ignore[attr-defined]
        title_row = tk.Frame(plan_content, bg=COLORS["panel"])
        title_row.pack(fill="x")
        self._label(title_row, "Today's study plan", size=14, bold=True, background=COLORS["panel"]).pack(side="left")
        self._label(title_row, f"{settings.get('daily_goal_minutes', 45)} min goal", size=9, bold=True, color=COLORS["accent"], background=COLORS["accent_light"], padx=9, pady=4).pack(side="right")
        self._label(plan_content, "Small, focused blocks beat last-minute cramming.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(4, 10))
        plan_vars: dict[str, tk.BooleanVar] = {}
        plan_bar = ttk.Progressbar(plan_content, maximum=sum(task["minutes"] for task in plan), mode="determinate")
        plan_bar.pack(fill="x", pady=(0, 7))
        plan_progress = self._label(plan_content, "", size=8, color=COLORS["muted"], background=COLORS["panel"])
        plan_progress.pack(anchor="w", pady=(0, 5))
        for task in plan:
            row = tk.Frame(plan_content, bg=COLORS["panel"])
            row.pack(fill="x", pady=5)
            variable = tk.BooleanVar(value=checks.get(task["id"], False))
            plan_vars[task["id"]] = variable
            check = tk.Checkbutton(
                row,
                variable=variable,
                command=lambda item=task, state=variable: self._complete_plan_task(item, state, plan, plan_vars, plan_bar, plan_progress),
                bg=COLORS["panel"],
                activebackground=COLORS["panel"],
                fg=COLORS["accent"],
                selectcolor=COLORS["panel"],
                relief="flat",
                bd=0,
                cursor="hand2",
            )
            check.pack(side="left", anchor="n", padx=(0, 5))
            task_text = tk.Frame(row, bg=COLORS["panel"])
            task_text.pack(side="left", fill="x", expand=True)
            self._label(task_text, task["title"], size=10, bold=True, background=COLORS["panel"]).pack(anchor="w")
            self._label(task_text, task["detail"], size=8, color=COLORS["muted"], background=COLORS["panel"], wrap=330).pack(anchor="w", pady=(2, 0))
            self._label(row, f"{task['minutes']}m", size=9, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(side="right", padx=(6, 0))
            self._button(row, "Open", lambda item=task: self._run_plan_task(item), compact=True).pack(side="right", padx=(4, 0))
        self._refresh_plan_progress(plan, plan_vars, plan_bar, plan_progress)

        focus_card = self._card(page, padding=18)
        focus_card.grid(row=4, column=1, sticky="nsew", padx=(7, 0), pady=(0, 16))
        focus_content = focus_card.content  # type: ignore[attr-defined]
        self._label(focus_content, "Focus on what will move your score", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(focus_content, "Your own attempts decide this ranking. New learners see a balanced syllabus mix.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=470).pack(anchor="w", pady=(4, 10))
        weak = weak_domains(self.profile)
        if weak:
            for domain, pct, count in weak[:4]:
                self._accuracy_row(focus_content, DOMAIN_LABELS.get(domain, domain), pct, f"{count} questions", parent_bg=COLORS["panel"])
        else:
            self._label(focus_content, "After a few sessions, your lowest-scoring subjects will appear here.", size=10, color=COLORS["muted"], background=COLORS["panel"], wrap=460).pack(anchor="w", pady=10)
            self._button(focus_content, "Choose a subject", lambda: self.show_page("practice")).pack(anchor="w", pady=(3, 0))
        self._label(page, "Blueprint for this track", size=13, bold=True).grid(row=5, column=0, columnspan=2, sticky="w", pady=(3, 8))
        blueprint = self._card(page, padding=15)
        blueprint.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        bcontent = blueprint.content  # type: ignore[attr-defined]
        for group, marks in track.weights.items():
            row = tk.Frame(bcontent, bg=COLORS["panel"])
            row.pack(fill="x", pady=3)
            label = track.bucket_labels.get(group, group.replace("_", " ").title())
            self._label(row, label, size=9, background=COLORS["panel"]).pack(side="left")
            self._label(row, f"{marks} / 100", size=9, bold=True, color=COLORS["accent"], background=COLORS["panel"]).pack(side="right")
        self._label(page, "Live current-affairs facts are not bundled. Use verified official sources and import dated questions for current events.", size=9, color=COLORS["muted"], wrap=850).grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 20))

    def _refresh_plan_progress(self, plan, variables, progress_bar, progress_label) -> None:
        total = sum(task["minutes"] for task in plan)
        completed = sum(task["minutes"] for task in plan if variables[task["id"]].get())
        progress_bar["value"] = completed
        progress_label.configure(text=f"{completed} of {total} planned minutes checked off")

    def _complete_plan_task(self, task, variable, plan, variables, progress_bar, progress_label) -> None:
        set_task_completion(self.profile, task["id"], variable.get())
        self._save_profile(quiet=True)
        self._refresh_plan_progress(plan, variables, progress_bar, progress_label)

    def _run_plan_task(self, task: dict[str, Any], launch_only: bool = False) -> None:
        action = task.get("action")
        if action == "flashcards":
            self.show_page("flashcards")
        elif action == "practice":
            self._start_session(count=10, mode="practice", domain=task.get("domain"))

    def _accuracy_row(self, parent: tk.Misc, label: str, pct: float, detail: str, *, parent_bg: str = COLORS["white"]) -> None:
        row = tk.Frame(parent, bg=parent_bg)
        row.pack(fill="x", pady=5)
        head = tk.Frame(row, bg=parent_bg)
        head.pack(fill="x")
        self._label(head, label, size=9, bold=True, background=parent_bg).pack(side="left")
        self._label(head, f"{_percent(pct)}  ·  {detail}", size=8, color=COLORS["muted"], background=parent_bg).pack(side="right")
        bar = ttk.Progressbar(row, maximum=100, value=max(0, min(100, pct)), mode="determinate")
        bar.pack(fill="x", pady=(4, 0))

    def _render_practice(self) -> None:
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        self._heading(page, "Practice by subject or take a full mock", "Choose an exam level, focus a topic, or use the syllabus-weighted timed mode. Everything works offline.")

        setup = self._card(page, padding=20)
        setup.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        content = setup.content  # type: ignore[attr-defined]
        self._label(content, "Set up your session", size=15, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 12))
        fields = tk.Frame(content, bg=COLORS["panel"])
        fields.pack(fill="x")
        for column in range(4):
            fields.grid_columnconfigure(column, weight=1)

        self._label(fields, "EXAM TRACK", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 5))
        self._label(fields, "SUBJECT", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(0, 5))
        self._label(fields, "TOPIC", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).grid(row=0, column=2, sticky="w", padx=(0, 10), pady=(0, 5))
        self._label(fields, "QUESTION COUNT", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).grid(row=0, column=3, sticky="w", pady=(0, 5))

        self._practice_track_var = tk.StringVar(value=TRACKS[self.current_track].name)
        track_names = [track.name for track in TRACKS.values()]
        track_ids_by_name = {track.name: track.id for track in TRACKS.values()}
        self._practice_track_combo = ttk.Combobox(fields, textvariable=self._practice_track_var, values=track_names, state="readonly")
        self._practice_track_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self._practice_track_combo.bind("<<ComboboxSelected>>", lambda _event: self._practice_track_changed(track_ids_by_name[self._practice_track_var.get()]))

        self._practice_domain_var = tk.StringVar(value="All subjects")
        self._practice_domain_combo = ttk.Combobox(fields, textvariable=self._practice_domain_var, state="readonly")
        self._practice_domain_combo.grid(row=1, column=1, sticky="ew", padx=(0, 10))
        self._practice_domain_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_topic_choices())
        self._topic_var = tk.StringVar(value="All topics")
        self._topic_combo = ttk.Combobox(fields, textvariable=self._topic_var, state="readonly")
        self._topic_combo.grid(row=1, column=2, sticky="ew", padx=(0, 10))
        self._count_var = tk.StringVar(value="10")
        self._count_combo = ttk.Combobox(fields, textvariable=self._count_var, values=("5", "10", "15", "20", "25", "50", "100"), state="readonly")
        self._count_combo.grid(row=1, column=3, sticky="ew")
        self._populate_practice_domains(self.current_track)

        lower = tk.Frame(content, bg=COLORS["panel"])
        lower.pack(fill="x", pady=(17, 0))
        mode_box = tk.Frame(lower, bg=COLORS["panel"])
        mode_box.pack(side="left", fill="x", expand=True)
        self._label(mode_box, "SESSION MODE", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(0, 5))
        self._mode_var = tk.StringVar(value="practice")
        for value, text in (("practice", "Learn as you go"), ("mock", "Timed mock")):
            ttk.Radiobutton(mode_box, text=text, variable=self._mode_var, value=value).pack(side="left", padx=(0, 14))
        self._negative_var = tk.BooleanVar(value=bool(self.profile["settings"].get("negative_marking", True)))
        ttk.Checkbutton(lower, text="Apply -1/3 per wrong answer in mock mode", variable=self._negative_var).pack(side="left", padx=14)
        self._button(lower, "Start session", self._start_from_practice, primary=True).pack(side="right")
        self._label(content, "A 100-question mock uses the selected blueprint. Shorter mocks use proportional sampling. Negative-marking rules vary by post; adjust this setting to match your notification.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(12, 0))

        subject_title = tk.Frame(page, bg=COLORS["bg"])
        subject_title.grid(row=2, column=0, sticky="ew", pady=(5, 8))
        self._label(subject_title, "Subject practice", size=15, bold=True).pack(side="left")
        self._label(subject_title, f"{len(self.question_pool):,} local questions available", size=9, color=COLORS["muted"]).pack(side="right")
        self._domain_grid = tk.Frame(page, bg=COLORS["bg"])
        self._domain_grid.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        self._render_domain_tiles(self.current_track)

        ca = self._card(page, padding=17)
        ca.grid(row=4, column=0, sticky="ew", pady=(0, 18))
        ca_content = ca.content  # type: ignore[attr-defined]
        self._label(ca_content, "Current affairs: keep it current", size=13, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(ca_content, "No stale headlines are built into the app. Use trusted official sources, then import a dated question pack so your mock reflects the right exam cycle.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(4, 10))
        link_row = tk.Frame(ca_content, bg=COLORS["panel"])
        link_row.pack(anchor="w")
        for label, url in CURRENT_AFFAIRS_SOURCES:
            self._button(link_row, label, lambda target=url: self._open_url(target), compact=True).pack(side="left", padx=(0, 6))
        self._button(link_row, "Import question pack", self._import_question_pack, compact=True).pack(side="left", padx=(4, 0))

    def _practice_track_changed(self, track_id: str) -> None:
        self.current_track = track_id
        self.profile["settings"]["track"] = track_id
        self._save_profile(quiet=True)
        self._practice_track_var.set(TRACKS[track_id].name)
        self._populate_practice_domains(track_id)
        self._render_domain_tiles(track_id)

    def _populate_practice_domains(self, track_id: str) -> None:
        if not hasattr(self, "_practice_domain_combo"):
            return
        domains = track_domain_ids(track_id, include_supplementary=True)
        self._practice_domain_by_label = {"All subjects": None}
        for domain in domains:
            self._practice_domain_by_label[DOMAIN_LABELS[domain]] = domain
        values = list(self._practice_domain_by_label)
        self._practice_domain_combo.configure(values=values)
        if self._practice_domain_var.get() not in values:
            self._practice_domain_var.set("All subjects")
        self._refresh_topic_choices()

    def _refresh_topic_choices(self) -> None:
        domain = getattr(self, "_practice_domain_by_label", {}).get(self._practice_domain_var.get())
        topics = sorted({q["topic"] for q in self.question_pool if domain is None or q["domain"] == domain})
        values = ["All topics", *topics]
        self._topic_combo.configure(values=values)
        if self._topic_var.get() not in values:
            self._topic_var.set("All topics")

    def _render_domain_tiles(self, track_id: str) -> None:
        if not hasattr(self, "_domain_grid") or not self._domain_grid.winfo_exists():
            return
        for child in self._domain_grid.winfo_children():
            child.destroy()
        domains = track_domain_ids(track_id, include_supplementary=True)
        columns = 3
        for column in range(columns):
            self._domain_grid.grid_columnconfigure(column, weight=1, uniform="subject")
        for index, domain in enumerate(domains):
            count = sum(1 for question in self.question_pool if question["domain"] == domain)
            row_index, column_index = divmod(index, columns)
            card = self._card(self._domain_grid, padding=13)
            card.grid(row=row_index, column=column_index, sticky="nsew", padx=5, pady=5)
            content = card.content  # type: ignore[attr-defined]
            self._label(content, DOMAIN_LABELS[domain], size=10, bold=True, background=COLORS["panel"], wrap=240).pack(anchor="w")
            self._label(content, f"{count} ready question{'s' if count != 1 else ''}", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(4, 8))
            if count:
                self._button(content, "Practise this subject", lambda selected=domain: self._start_session(count=min(10, sum(1 for q in self.question_pool if q["domain"] == selected)), mode="practice", domain=selected), compact=True).pack(anchor="w")
            elif domain == "current_affairs":
                self._button(content, "Import dated questions", self._import_question_pack, compact=True).pack(anchor="w")
            else:
                self._label(content, "Import a question pack to add items.", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")

    def _start_from_practice(self) -> None:
        label = self._practice_domain_var.get()
        domain = self._practice_domain_by_label.get(label)
        topic_label = self._topic_var.get()
        topic = None if topic_label == "All topics" else topic_label
        try:
            count = int(self._count_var.get())
        except ValueError:
            count = 10
        self._start_session(count=count, mode=self._mode_var.get(), domain=domain, topic=topic)

    def _start_session(
        self,
        *,
        count: int,
        mode: str,
        domain: str | None = None,
        topic: str | None = None,
    ) -> None:
        if mode not in {"practice", "mock"}:
            mode = "practice"
        try:
            selection = select_questions(
                self.question_pool,
                self.current_track,
                count,
                domain=domain,
                topic=topic,
                rng=random.Random(),
                adaptive=(mode == "practice"),
                profile=self.profile,
            )
        except (NotEnoughQuestionsError, ValueError) as exc:
            messagebox.showinfo(APP_TITLE, str(exc))
            if "current_affairs" == domain:
                self.show_page("practice")
            return

        if mode == "mock":
            duration = max(60, int(TRACKS[self.current_track].duration_minutes * 60 * count / 100))
            negative_setting = getattr(self, "_negative_var", None)
            apply_penalty = negative_setting.get() if negative_setting is not None else bool(self.profile["settings"].get("negative_marking", True))
            penalty = 1 / 3 if apply_penalty else 0.0
        else:
            duration = 0
            penalty = 0.0
        started = time.monotonic()
        self.session = {
            "track": self.current_track,
            "mode": mode,
            "questions": selection["questions"],
            "answers": {},
            "checked": set(),
            "flagged": set(),
            "index": 0,
            "coverage": selection["coverage"],
            "notes": selection["notes"],
            "started_monotonic": started,
            "deadline": started + duration if duration else None,
            "duration": duration,
            "penalty": penalty,
        }
        self._finishing = False
        self.show_page("quiz")

    def _render_quiz(self) -> None:
        if self.session is None:
            self.show_page("practice")
            return
        page = self._new_scroll_page()
        session = self.session
        questions = session["questions"]
        index = session["index"]
        question = questions[index]
        qid = question["id"]
        total = len(questions)
        answered = sum(1 for item in questions if session["answers"].get(item["id"]))

        top = tk.Frame(page, bg=COLORS["bg"])
        top.pack(fill="x", pady=(2, 10))
        title = "Learn as you go" if session["mode"] == "practice" else "Timed mock exam"
        self._label(top, title, size=18, bold=True).pack(side="left")
        if session["mode"] == "mock":
            self.timer_label = self._label(top, "", size=16, bold=True, color=COLORS["gold"], background=COLORS["gold_light"], padx=12, pady=7)
            self.timer_label.pack(side="right")
        else:
            self._label(top, "Untimed · explanation after each answer", size=9, color=COLORS["muted"]).pack(side="right")

        progress = tk.Frame(page, bg=COLORS["bg"])
        progress.pack(fill="x", pady=(0, 12))
        self._label(progress, f"Question {index + 1} of {total}", size=10, bold=True).pack(side="left")
        self._label(progress, f"Answered {answered}/{total}", size=9, color=COLORS["muted"]).pack(side="right")
        progressbar = ttk.Progressbar(progress, maximum=total, value=index + 1, mode="determinate")
        progressbar.pack(side="bottom", fill="x", pady=(7, 0))

        panel = self._card(page, padding=22)
        panel.pack(fill="x", pady=(0, 12))
        content = panel.content  # type: ignore[attr-defined]
        meta = tk.Frame(content, bg=COLORS["panel"])
        meta.pack(fill="x", pady=(0, 12))
        self._label(meta, DOMAIN_LABELS.get(question["domain"], question["domain"]), size=8, bold=True, color=COLORS["accent"], background=COLORS["accent_light"], padx=9, pady=5).pack(side="left")
        self._label(meta, question.get("topic", "General practice"), size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(side="left", padx=10)
        self._label(meta, f"Level {question.get('difficulty', 4)}/10", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(side="right")
        self._label(content, question["question"], size=15, bold=True, background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(0, 17))

        self._option_var = tk.StringVar(value=session["answers"].get(qid, ""))
        is_checked = session["mode"] == "practice" and qid in session["checked"]
        for letter in "ABCD":
            choice_text = question["options"][letter]
            choice_bg = COLORS["panel_alt"]
            choice_fg = COLORS["ink"]
            if is_checked and letter == question["answer"]:
                choice_bg, choice_fg = COLORS["accent_light"], COLORS["accent_dark"]
            elif is_checked and letter == session["answers"].get(qid):
                choice_bg, choice_fg = COLORS["red_light"], COLORS["red"]
            row = tk.Frame(content, bg=choice_bg, highlightbackground=COLORS["border"], highlightthickness=1, padx=8, pady=6)
            row.pack(fill="x", pady=4)
            radio = tk.Radiobutton(
                row,
                text=f"{letter}.  {choice_text}",
                variable=self._option_var,
                value=letter,
                command=lambda selected=letter, item=qid: self._save_answer(item, selected),
                state="disabled" if is_checked else "normal",
                anchor="w",
                justify="left",
                wraplength=900,
                font=(FONT, 10, "bold" if is_checked and letter == question["answer"] else "normal"),
                fg=choice_fg,
                bg=choice_bg,
                activeforeground=COLORS["accent"],
                activebackground=choice_bg,
                selectcolor=choice_bg,
                relief="flat",
                bd=0,
                padx=7,
                pady=3,
                cursor="hand2",
            )
            radio.pack(fill="x", anchor="w")

        if is_checked:
            correct = session["answers"].get(qid) == question["answer"]
            feedback_bg = COLORS["accent_light"] if correct else COLORS["red_light"]
            feedback_fg = COLORS["accent_dark"] if correct else COLORS["red"]
            feedback = tk.Frame(content, bg=feedback_bg, padx=13, pady=11)
            feedback.pack(fill="x", pady=(13, 2))
            result_title = "Correct — keep going." if correct else f"Not quite. The answer is {question['answer']}."
            self._label(feedback, result_title, size=10, bold=True, color=feedback_fg, background=feedback_bg).pack(anchor="w")
            if question.get("explanation"):
                self._label(feedback, question["explanation"], size=9, color=COLORS["ink"], background=feedback_bg, wrap=900).pack(anchor="w", pady=(5, 0))
            if question.get("source_hint"):
                self._label(feedback, question["source_hint"], size=8, color=COLORS["muted"], background=feedback_bg, wrap=900).pack(anchor="w", pady=(5, 0))
        elif session["mode"] == "practice":
            self._label(content, "Choose one answer, then check it to see the worked explanation.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(10, 0))

        nav = tk.Frame(page, bg=COLORS["bg"])
        nav.pack(fill="x", pady=(0, 14))
        self._button(nav, "Previous", lambda: self._navigate_question(index - 1), compact=True, state="normal" if index else "disabled").pack(side="left")
        if session["mode"] == "practice":
            if not is_checked:
                self._button(nav, "Check answer", self._check_answer, primary=True).pack(side="right", padx=(8, 0))
            next_text = "Finish practice" if index == total - 1 else "Next question"
            self._button(nav, next_text, self._next_question, primary=is_checked).pack(side="right")
        else:
            flagged = index in session["flagged"]
            self._button(nav, "Unmark for review" if flagged else "Mark for review", self._toggle_flag, compact=True).pack(side="left", padx=(8, 0))
            self._button(nav, "Submit mock", self._submit_session, primary=True).pack(side="right", padx=(8, 0))
            self._button(nav, "Next question" if index < total - 1 else "Finish mock", self._next_question).pack(side="right")

        map_card = self._card(page, padding=15)
        map_card.pack(fill="x", pady=(0, 18))
        map_content = map_card.content  # type: ignore[attr-defined]
        map_header = tk.Frame(map_content, bg=COLORS["panel"])
        map_header.pack(fill="x", pady=(0, 8))
        self._label(map_header, "Question map", size=11, bold=True, background=COLORS["panel"]).pack(side="left")
        self._label(map_header, "Green = answered · gold = marked for review", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(side="right")
        grid = tk.Frame(map_content, bg=COLORS["panel"])
        grid.pack(anchor="w")
        self._question_map_buttons = []
        for number in range(total):
            row, column = divmod(number, 10)
            button = tk.Button(
                grid,
                text=str(number + 1),
                width=3,
                height=1,
                font=(FONT, 8, "bold"),
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda item=number: self._navigate_question(item),
            )
            button.grid(row=row, column=column, padx=3, pady=3)
            self._question_map_buttons.append(button)
        self._update_question_map()
        if session["mode"] == "mock" and self._timer_job is None:
            self._update_timer()

    def _save_answer(self, question_id: str, letter: str) -> None:
        if self.session is None:
            return
        if question_id in self.session["checked"]:
            return
        self.session["answers"][question_id] = letter
        self._update_question_map()

    def _update_question_map(self) -> None:
        if self.session is None or not hasattr(self, "_question_map_buttons"):
            return
        current = self.session["index"]
        for index, button in enumerate(self._question_map_buttons):
            question = self.session["questions"][index]
            answer = self.session["answers"].get(question["id"])
            if self.session["mode"] == "practice" and question["id"] in self.session["checked"]:
                background = COLORS["accent"] if answer == question["answer"] else COLORS["red"]
                foreground = COLORS["white"]
            elif index in self.session["flagged"]:
                background, foreground = COLORS["gold_light"], COLORS["gold"]
            elif answer:
                background, foreground = COLORS["blue_light"], COLORS["blue"]
            else:
                background, foreground = COLORS["panel_alt"], COLORS["muted"]
            if index == current:
                background, foreground = COLORS["nav"], COLORS["white"]
            button.configure(bg=background, fg=foreground, activebackground=background, activeforeground=foreground)

    def _navigate_question(self, index: int) -> None:
        if self.session is None:
            return
        if 0 <= index < len(self.session["questions"]):
            self.session["index"] = index
            self._render_quiz()

    def _next_question(self) -> None:
        if self.session is None:
            return
        if self.session["index"] + 1 < len(self.session["questions"]):
            self._navigate_question(self.session["index"] + 1)
        else:
            self._submit_session()

    def _check_answer(self) -> None:
        if self.session is None:
            return
        question = self.session["questions"][self.session["index"]]
        answer = self.session["answers"].get(question["id"], "")
        if not answer:
            messagebox.showinfo(APP_TITLE, "Choose an option before checking your answer.")
            return
        self.session["checked"].add(question["id"])
        self._render_quiz()

    def _toggle_flag(self) -> None:
        if self.session is None:
            return
        index = self.session["index"]
        if index in self.session["flagged"]:
            self.session["flagged"].remove(index)
        else:
            self.session["flagged"].add(index)
        self._render_quiz()

    def _submit_session(self, *, automatic: bool = False) -> None:
        if self.session is None or self._finishing:
            return
        session = self.session
        unanswered = sum(1 for question in session["questions"] if not session["answers"].get(question["id"]))
        if not automatic and session["mode"] == "mock" and unanswered:
            if not messagebox.askyesno(APP_TITLE, f"{unanswered} question(s) are unanswered. Submit this mock now?"):
                return
        self._finishing = True
        self._cancel_timer()
        elapsed = max(0, int(time.monotonic() - session["started_monotonic"]))
        try:
            self.profile, result = update_after_session(
                self.profile,
                session["questions"],
                session["answers"],
                track_id=session["track"],
                elapsed_seconds=elapsed,
                penalty_per_wrong=session["penalty"],
            )
            self.profile["settings"]["track"] = session["track"]
            self.last_result = {
                **result,
                "track": session["track"],
                "mode": session["mode"],
                "questions": session["questions"],
                "answers": dict(session["answers"]),
                "elapsed_seconds": elapsed,
                "penalty": session["penalty"],
                "notes": list(session["notes"]),
                "coverage": dict(session["coverage"]),
            }
            self.session = None
            self._save_profile()
            self.show_page("results")
        except Exception as exc:
            self._finishing = False
            messagebox.showerror(APP_TITLE, f"Could not finish this session safely.\n\n{exc}")

    def _cancel_timer(self) -> None:
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except tk.TclError:
                pass
            self._timer_job = None

    def _update_timer(self) -> None:
        self._timer_job = None
        if self.session is None or self.session["mode"] != "mock" or self.current_page != "quiz":
            return
        remaining = max(0, int(self.session["deadline"] - time.monotonic()))
        if hasattr(self, "timer_label") and self.timer_label.winfo_exists():
            self.timer_label.configure(text=f"TIME LEFT  {_minutes(remaining)}", fg=COLORS["red"] if remaining < 300 else COLORS["gold"])
        if remaining <= 0:
            self._submit_session(automatic=True)
            return
        self._timer_job = self.after(1000, self._update_timer)

    def _render_results(self) -> None:
        if self.last_result is None:
            self.show_page("home")
            return
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        result = self.last_result
        track = TRACKS[result["track"]]
        score = result["score_pct"]
        label = "Strong work — keep your review loop going." if score >= 80 else "Good diagnostic — turn the misses into your next study targets." if score >= 55 else "A useful baseline — focus on the explanations and build step by step."
        self._heading(page, "Session complete", f"{track.name} · {'Timed mock' if result['mode'] == 'mock' else 'Practice'} · {_minutes(result['elapsed_seconds'])}")

        hero = tk.Frame(page, bg=COLORS["nav"], padx=22, pady=21)
        hero.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        hero.grid_columnconfigure(0, weight=1)
        score_color = "#9ce4c2" if score >= 70 else "#ffd887" if score >= 45 else "#ffaaa2"
        self._label(hero, _percent(score), size=34, bold=True, color=score_color, background=COLORS["nav"]).grid(row=0, column=0, sticky="w")
        self._label(hero, label, size=11, bold=True, color=COLORS["white"], background=COLORS["nav"], wrap=670).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._label(hero, f"{result['correct']} correct  ·  {result['wrong']} wrong  ·  {result['skipped']} skipped", size=10, color="#c7d9d1", background=COLORS["nav"]).grid(row=0, column=1, sticky="e", padx=(15, 0))
        if result["penalty"]:
            self._label(hero, f"Net marks: {result['net_marks']:.2f} / {result['total']}  ·  wrong-answer penalty: 1/3", size=9, color="#c7d9d1", background=COLORS["nav"]).grid(row=1, column=1, sticky="e", padx=(15, 0), pady=(5, 0))

        actions = tk.Frame(page, bg=COLORS["bg"])
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        weak_this_session = sorted(result["by_domain"].items(), key=lambda item: item[1]["accuracy_pct"])
        target_domain = weak_this_session[0][0] if weak_this_session else None
        target_count = min(10, sum(1 for question in self.question_pool if question["domain"] == target_domain)) if target_domain else 0
        self._button(actions, "Practise the weakest subject", lambda: self._start_session(count=target_count, mode="practice", domain=target_domain), primary=True, state="normal" if target_count else "disabled").pack(side="left")
        self._button(actions, f"Review due flashcards ({len(due_flashcards(self.profile))})", lambda: self.show_page("flashcards")).pack(side="left", padx=8)
        self._button(actions, "Back to overview", lambda: self.show_page("home"), compact=True).pack(side="right")

        breakdown = self._card(page, padding=18)
        breakdown.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        bcontent = breakdown.content  # type: ignore[attr-defined]
        self._label(bcontent, "Subject breakdown", size=13, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 7))
        for domain, values in sorted(result["by_domain"].items(), key=lambda item: item[1]["accuracy_pct"]):
            self._accuracy_row(
                bcontent,
                DOMAIN_LABELS.get(domain, domain),
                values["accuracy_pct"],
                f"{values['correct']}/{values['total']} correct",
                parent_bg=COLORS["panel"],
            )
        for note in result["notes"]:
            self._label(bcontent, note, size=8, color=COLORS["gold"], background=COLORS["gold_light"], wrap=900, padx=10, pady=7).pack(fill="x", pady=(7, 0))

        self._label(page, "Answer review", size=15, bold=True).grid(row=4, column=0, sticky="w", pady=(3, 8))
        wrong = [item for item in result["reviews"] if not item["was_correct"]]
        if wrong:
            self._label(page, f"{len(wrong)} question(s) were incorrect or left blank. Each mistake has been added to your spaced-review deck.", size=9, color=COLORS["muted"], wrap=900).grid(row=5, column=0, sticky="w", pady=(0, 8))
        else:
            self._label(page, "All answers correct. Review the key explanations and keep practising mixed topics.", size=9, color=COLORS["muted"], wrap=900).grid(row=5, column=0, sticky="w", pady=(0, 8))

        self._show_all_review_var = tk.BooleanVar(value=False)
        review_toggle = ttk.Checkbutton(page, text="Show every question (including correct answers)", variable=self._show_all_review_var, command=self._refresh_result_review)
        review_toggle.grid(row=6, column=0, sticky="w", pady=(0, 8))
        self._review_container = tk.Frame(page, bg=COLORS["bg"])
        self._review_container.grid(row=7, column=0, sticky="ew")
        self._populate_result_review()
        self._label(page, "Practice scores are learning signals, not official marks or a guarantee of selection. Always check the current post notification.", size=8, color=COLORS["muted"], wrap=900).grid(row=8, column=0, sticky="w", pady=(15, 24))

    def _refresh_result_review(self) -> None:
        self._populate_result_review()

    def _populate_result_review(self) -> None:
        if not hasattr(self, "_review_container") or not self._review_container.winfo_exists() or self.last_result is None:
            return
        for child in self._review_container.winfo_children():
            child.destroy()
        reviews = self.last_result["reviews"]
        if not getattr(self, "_show_all_review_var", tk.BooleanVar(value=False)).get():
            reviews = [item for item in reviews if not item["was_correct"]]
        for number, item in enumerate(reviews, start=1):
            correct_letter = item["correct_answer"]
            correct_text = item["options"].get(correct_letter, "")
            user_letter = item["user_answer"]
            user_text = f"{user_letter}. {item['options'].get(user_letter, '')}" if user_letter else "Not answered"
            card = self._card(self._review_container, padding=14)
            card.pack(fill="x", pady=5)
            content = card.content  # type: ignore[attr-defined]
            label = f"{number}. {item['topic']}  ·  {DOMAIN_LABELS.get(item['domain'], item['domain'])}"
            self._label(content, label, size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")
            self._label(content, item["question"], size=10, bold=True, background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(5, 7))
            self._label(content, f"Your answer: {user_text}", size=9, color=COLORS["red"] if not item["was_correct"] else COLORS["accent"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=2)
            self._label(content, f"Correct answer: {correct_letter}. {correct_text}", size=9, bold=True, color=COLORS["accent_dark"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=2)
            if item.get("explanation"):
                self._label(content, item["explanation"], size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(5, 0))
            if item.get("source_hint"):
                self._label(content, item["source_hint"], size=8, color=COLORS["muted_light"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(4, 0))

    def _render_flashcards(self, preserve_queue: bool = False) -> None:
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        cards = self.profile.get("flashcards", [])
        if preserve_queue:
            queue = getattr(self, "_flashcard_queue", [])
            due_ids = set(queue)
            due = [card for card in due_flashcards(self.profile) if card.get("id") in due_ids]
        else:
            due = due_flashcards(self.profile)
            self._flashcard_queue = [card["id"] for card in due]
            self._flashcard_index = 0
            self._flashcard_revealed = False
        self._heading(page, "Remember more with spaced review", "Recall the answer first, reveal it, then rate how difficult it felt. The schedule adjusts to your recall.")
        stats_card = self._card(page, padding=17)
        stats_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        stats_content = stats_card.content  # type: ignore[attr-defined]
        self._label(stats_content, f"{len(due)} due now  ·  {len(cards)} total cards", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(stats_content, "Again brings a card back in about 10 minutes; Hard, Good and Easy increase the interval.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(5, 0))

        if due:
            if not preserve_queue:
                self._flashcard_queue = [card["id"] for card in due]
                self._flashcard_index = 0
                self._flashcard_revealed = False
            else:
                self._flashcard_index = min(self._flashcard_index, len(self._flashcard_queue) - 1)
            self._render_flashcard_item(page, due)
        else:
            empty = self._card(page, padding=24)
            empty.grid(row=2, column=0, sticky="ew", pady=(0, 14))
            empty_content = empty.content  # type: ignore[attr-defined]
            self._label(empty_content, "You're all caught up.", size=17, bold=True, color=COLORS["accent"], background=COLORS["panel"]).pack(anchor="w")
            self._label(empty_content, "Cards created from mistakes will appear here when they are due. Keep taking short quizzes to grow your deck.", size=10, color=COLORS["muted"], background=COLORS["panel"], wrap=850).pack(anchor="w", pady=(5, 0))

        if cards:
            self._label(page, "Your review deck", size=14, bold=True).grid(row=3, column=0, sticky="w", pady=(5, 8))
            for card in sorted(cards, key=lambda item: item.get("next_review", ""))[:100]:
                item_card = self._card(page, padding=13)
                item_card.grid(sticky="ew", pady=4)
                item_content = item_card.content  # type: ignore[attr-defined]
                top = tk.Frame(item_content, bg=COLORS["panel"])
                top.pack(fill="x")
                self._label(top, f"{DOMAIN_LABELS.get(card.get('domain', ''), card.get('domain', ''))}  ·  {card.get('topic', '')}", size=8, bold=True, color=COLORS["accent"], background=COLORS["panel"]).pack(side="left")
                self._label(top, f"Due {card.get('next_review', '')[:10]}", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(side="right")
                self._label(item_content, card.get("question", ""), size=9, bold=True, background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(5, 3))
                self._label(item_content, f"Answer: {card.get('answer', '')}", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w")
        else:
            self._label(page, "Your deck is empty", size=14, bold=True).grid(row=3, column=0, sticky="w", pady=(6, 4))
            self._label(page, "Incorrect and skipped answers become review cards automatically when you finish a session.", size=9, color=COLORS["muted"], wrap=900).grid(row=4, column=0, sticky="w", pady=(0, 18))

    def _render_flashcard_item(self, page: tk.Frame, due: list[dict[str, Any]]) -> None:
        for child in getattr(self, "_flashcard_panel_children", []):
            try:
                child.destroy()
            except tk.TclError:
                pass
        card_id = self._flashcard_queue[self._flashcard_index]
        card = next((item for item in due if item["id"] == card_id), None)
        if card is None:
            return
        panel = self._card(page, padding=22)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self._flashcard_panel_children = [panel]
        content = panel.content  # type: ignore[attr-defined]
        self._label(content, f"CARD {self._flashcard_index + 1} OF {len(self._flashcard_queue)}", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")
        self._label(content, f"{DOMAIN_LABELS.get(card.get('domain', ''), card.get('domain', ''))}  ·  {card.get('topic', '')}", size=9, color=COLORS["accent"], background=COLORS["panel"]).pack(anchor="w", pady=(4, 8))
        self._label(content, card.get("question", ""), size=15, bold=True, background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(0, 12))
        for letter, option in card.get("options", {}).items():
            self._label(content, f"{letter}. {option}", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=1)
        self._flashcard_rating_frame = tk.Frame(content, bg=COLORS["panel"])
        if self._flashcard_revealed:
            answer_panel = tk.Frame(content, bg=COLORS["accent_light"], padx=12, pady=10)
            answer_panel.pack(fill="x", pady=(12, 3))
            self._label(answer_panel, f"Answer: {card.get('answer', '')}", size=11, bold=True, color=COLORS["accent_dark"], background=COLORS["accent_light"], wrap=900).pack(anchor="w")
            if card.get("explanation"):
                self._label(answer_panel, card["explanation"], size=9, color=COLORS["ink"], background=COLORS["accent_light"], wrap=900).pack(anchor="w", pady=(5, 0))
            self._flashcard_rating_frame.pack(fill="x", pady=(12, 0))
            self._label(self._flashcard_rating_frame, "How well did you recall it?", size=9, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 7))
            ratings = (("Again", "again", "Danger.TButton"), ("Hard", "hard", "Soft.TButton"), ("Good", "good", "Accent.TButton"), ("Easy", "easy", "Soft.TButton"))
            for label, value, style in ratings:
                ttk.Button(self._flashcard_rating_frame, text=label, command=lambda selected=value: self._rate_flashcard(selected), style=style).pack(side="left", padx=(0, 7))
        else:
            self._button(content, "Reveal answer", self._reveal_flashcard, primary=True).pack(anchor="w", pady=(13, 0))

    def _reveal_flashcard(self) -> None:
        self._flashcard_revealed = True
        self._render_flashcards(preserve_queue=True)

    def _rate_flashcard(self, quality: str) -> None:
        queue = getattr(self, "_flashcard_queue", [])
        index = getattr(self, "_flashcard_index", 0)
        if index >= len(queue):
            return
        card_id = queue[index]
        try:
            schedule_flashcard(self.profile, card_id, quality)
            self._save_profile()
        except (KeyError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._flashcard_index += 1
        self._flashcard_revealed = False
        if self._flashcard_index >= len(queue):
            self.show_page("flashcards")
            return
        self._render_flashcard_queue_next()

    def _render_flashcard_queue_next(self) -> None:
        if self.current_page != "flashcards":
            return
        # Rebuild the scroll page while retaining the current queue snapshot.
        queue_ids = getattr(self, "_flashcard_queue", [])
        index = getattr(self, "_flashcard_index", 0)
        due = [card for card in self.profile.get("flashcards", []) if card.get("id") in queue_ids]
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        self._heading(page, "Remember more with spaced review", "Recall the answer first, reveal it, then rate how difficult it felt. The schedule adjusts to your recall.")
        stats_card = self._card(page, padding=17)
        stats_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        stats_content = stats_card.content  # type: ignore[attr-defined]
        self._label(stats_content, f"{len(due_flashcards(self.profile))} due now  ·  {len(self.profile.get('flashcards', []))} total cards", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        panel = self._card(page, padding=22)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self._flashcard_panel_children = [panel]
        card_id = queue_ids[index]
        card = next(item for item in due if item["id"] == card_id)
        content = panel.content  # type: ignore[attr-defined]
        self._label(content, f"CARD {index + 1} OF {len(queue_ids)}", size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")
        self._label(content, f"{DOMAIN_LABELS.get(card.get('domain', ''), card.get('domain', ''))}  ·  {card.get('topic', '')}", size=9, color=COLORS["accent"], background=COLORS["panel"]).pack(anchor="w", pady=(4, 8))
        self._label(content, card.get("question", ""), size=15, bold=True, background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(0, 12))
        for letter, option in card.get("options", {}).items():
            self._label(content, f"{letter}. {option}", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=1)
        if self._flashcard_revealed:
            answer_panel = tk.Frame(content, bg=COLORS["accent_light"], padx=12, pady=10)
            answer_panel.pack(fill="x", pady=(12, 3))
            self._label(answer_panel, f"Answer: {card.get('answer', '')}", size=11, bold=True, color=COLORS["accent_dark"], background=COLORS["accent_light"], wrap=900).pack(anchor="w")
            if card.get("explanation"):
                self._label(answer_panel, card["explanation"], size=9, color=COLORS["ink"], background=COLORS["accent_light"], wrap=900).pack(anchor="w", pady=(5, 0))
            row = tk.Frame(content, bg=COLORS["panel"])
            row.pack(fill="x", pady=(12, 0))
            self._label(row, "How well did you recall it?", size=9, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 7))
            for label, value, style in (("Again", "again", "Danger.TButton"), ("Hard", "hard", "Soft.TButton"), ("Good", "good", "Accent.TButton"), ("Easy", "easy", "Soft.TButton")):
                ttk.Button(row, text=label, command=lambda selected=value: self._rate_flashcard(selected), style=style).pack(side="left", padx=(0, 7))
        else:
            self._button(content, "Reveal answer", self._reveal_flashcard, primary=True).pack(anchor="w", pady=(13, 0))

    def _on_close(self) -> None:
        self._cancel_timer()
        self.destroy()

    def _open_url(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not open this link.\n\n{exc}")

    def _render_progress(self) -> None:
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        stats = self.profile["stats"]
        questions = stats.get("questions", 0)
        score = 100.0 * stats.get("correct", 0) / questions if questions else 0.0
        self._heading(page, "Your progress, made visible", "Use the trend to adjust your study plan. Small samples are noisy; compare several sessions rather than one score.")

        metrics = tk.Frame(page, bg=COLORS["bg"])
        metrics.grid(row=1, column=0, sticky="ew", pady=(0, 13))
        for column in range(4):
            metrics.grid_columnconfigure(column, weight=1, uniform="progress_metric")
        values = (
            ("OVERALL ACCURACY", _percent(score), COLORS["accent"]),
            ("TOTAL QUESTIONS", f"{questions:,}", COLORS["blue"]),
            ("COMPLETED SESSIONS", str(stats.get("sessions", 0)), COLORS["purple"]),
            ("CURRENT STREAK", f"{stats.get('streak', 0)} days", COLORS["gold"]),
        )
        for index, (label, value, color) in enumerate(values):
            card = self._card(metrics, padding=15)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 0 if index == 3 else 5))
            content = card.content  # type: ignore[attr-defined]
            self._label(content, label, size=8, bold=True, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w")
            self._label(content, value, size=20, bold=True, color=color, background=COLORS["panel"]).pack(anchor="w", pady=(7, 0))

        chart_card = self._card(page, padding=18)
        chart_card.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        chart_content = chart_card.content  # type: ignore[attr-defined]
        self._label(chart_content, "Recent score trend", size=13, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(chart_content, "Net score percentage by session (last 20 saved attempts).", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(3, 8))
        chart = tk.Canvas(chart_content, height=190, bg=COLORS["panel"], highlightthickness=0)
        chart.pack(fill="x")
        chart.bind("<Configure>", lambda event: self._draw_score_trend(chart, event.width, event.height))
        self.after(30, lambda: self._draw_score_trend(chart, chart.winfo_width(), chart.winfo_height()))

        subjects = self._card(page, padding=18)
        subjects.grid(row=3, column=0, sticky="ew", pady=(0, 13))
        subject_content = subjects.content  # type: ignore[attr-defined]
        self._label(subject_content, "Accuracy by subject", size=13, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 6))
        ranked = weak_domains(self.profile, minimum_questions=1)
        if ranked:
            for domain, pct, count in ranked:
                self._accuracy_row(subject_content, DOMAIN_LABELS.get(domain, domain), pct, f"{count} answered", parent_bg=COLORS["panel"])
        else:
            self._label(subject_content, "Finish a quiz to start building subject-level progress.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=5)

        recent = self._card(page, padding=18)
        recent.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        recent_content = recent.content  # type: ignore[attr-defined]
        self._label(recent_content, "Recent sessions", size=13, bold=True, background=COLORS["panel"]).pack(anchor="w", pady=(0, 8))
        columns = ("date", "track", "count", "correct", "score", "time")
        table = ttk.Treeview(recent_content, columns=columns, show="headings", height=min(9, max(3, len(self.profile.get("sessions", [])))))
        headers = (("date", "Date"), ("track", "Track"), ("count", "Questions"), ("correct", "Correct"), ("score", "Net score"), ("time", "Time"))
        for key, label in headers:
            table.heading(key, text=label)
            table.column(key, anchor="w" if key in {"date", "track"} else "center", width=150 if key == "date" else 130)
        for session in reversed(self.profile.get("sessions", [])[-50:]):
            try:
                parsed_date = str(session.get("date", ""))[:16].replace("T", " ")
                track_name = TRACKS.get(session.get("track", ""), None)
                track_label = track_name.short_name if track_name else str(session.get("track", "Legacy"))
                session_score = float(session.get("score_pct", 0))
                if session.get("net_marks") is None and session.get("count"):
                    session_score = float(session.get("correct", 0)) / max(1, int(session.get("count", 1))) * 100
                table.insert("", "end", values=(
                    parsed_date,
                    track_label,
                    session.get("count", 0),
                    session.get("correct", 0),
                    _percent(session_score),
                    _minutes(session.get("elapsed_seconds", 0)),
                ))
            except (TypeError, ValueError, tk.TclError):
                continue
        table.pack(fill="x")
        if not self.profile.get("sessions"):
            self._label(recent_content, "No saved sessions yet. Start with a 10-question practice.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(6, 0))

    def _draw_score_trend(self, canvas: tk.Canvas, width: int, height: int) -> None:
        if not canvas.winfo_exists():
            return
        canvas.delete("all")
        trend = self.profile.get("stats", {}).get("trend", [])[-20:]
        values = []
        for item in trend:
            try:
                values.append(float(item.get("score_pct", 0)) if isinstance(item, dict) else float(item))
            except (TypeError, ValueError):
                continue
        if not values:
            canvas.create_text(width / 2, height / 2, text="Your first session will appear here", fill=COLORS["muted"], font=(FONT, 10))
            return
        left, right, top, bottom = 42, max(50, width - 20), 14, max(40, height - 28)
        for mark in (0, 50, 100):
            y = bottom - (bottom - top) * mark / 100
            canvas.create_line(left, y, right, y, fill=COLORS["border"])
            canvas.create_text(left - 8, y, text=f"{mark}%", fill=COLORS["muted"], anchor="e", font=(FONT, 8))
        if len(values) == 1:
            x_values = [(left + right) / 2]
        else:
            x_values = [left + (right - left) * index / (len(values) - 1) for index in range(len(values))]
        points = []
        for x, value in zip(x_values, values):
            y = bottom - (bottom - top) * max(0, min(100, value)) / 100
            points.extend((x, y))
        if len(points) >= 4:
            canvas.create_line(*points, fill=COLORS["accent"], width=3, smooth=True)
        for x, y in zip(points[::2], points[1::2]):
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=COLORS["accent"], outline=COLORS["white"], width=1)
        canvas.create_text(left, height - 7, text="Oldest", fill=COLORS["muted"], anchor="w", font=(FONT, 8))
        canvas.create_text(right, height - 7, text="Most recent", fill=COLORS["muted"], anchor="e", font=(FONT, 8))

    def _render_settings(self) -> None:
        page = self._new_scroll_page()
        page.grid_columnconfigure(0, weight=1)
        self._heading(page, "Your local question library", "Bring your own current-affairs and subject packs, save a backup, or open the official syllabus. No account or API key is required.")

        bank_card = self._card(page, padding=19)
        bank_card.grid(row=1, column=0, sticky="ew", pady=(0, 13))
        bank = bank_card.content  # type: ignore[attr-defined]
        self._label(bank, "Question library", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        domain_counts: dict[str, int] = {}
        for question in self.question_pool:
            domain_counts[question["domain"]] = domain_counts.get(question["domain"], 0) + 1
        built_in_count = len(self.question_pool) - len(self.profile.get("custom_questions", []))
        self._label(bank, f"{built_in_count} bundled original practice questions + {len(self.profile.get('custom_questions', []))} imported questions.", size=9, color=COLORS["muted"], background=COLORS["panel"]).pack(anchor="w", pady=(5, 9))
        sorted_domains = sorted(domain_counts.items(), key=lambda item: DOMAIN_LABELS.get(item[0], item[0]))
        self._label(bank, "  ·  ".join(f"{DOMAIN_LABELS.get(domain, domain)}: {count}" for domain, count in sorted_domains), size=8, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(0, 10))
        buttons = tk.Frame(bank, bg=COLORS["panel"])
        buttons.pack(anchor="w")
        self._button(buttons, "Import question pack (JSON)", self._import_question_pack, primary=True).pack(side="left", padx=(0, 7))
        self._button(buttons, "Export progress backup", self._export_backup).pack(side="left", padx=7)
        self._button(buttons, "Export flashcards (CSV)", self._export_flashcards).pack(side="left", padx=7)

        goals = self._card(page, padding=19)
        goals.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        goal_content = goals.content  # type: ignore[attr-defined]
        self._label(goal_content, "Study preferences", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        goal_row = tk.Frame(goal_content, bg=COLORS["panel"])
        goal_row.pack(fill="x", pady=(10, 0))
        self._label(goal_row, "Daily study goal", size=9, bold=True, background=COLORS["panel"]).pack(side="left", padx=(0, 10))
        goal_var = tk.StringVar(value=str(self.profile["settings"].get("daily_goal_minutes", 45)))
        goal_combo = ttk.Combobox(goal_row, textvariable=goal_var, values=("15", "30", "45", "60", "90", "120"), state="readonly", width=8)
        goal_combo.pack(side="left")
        goal_combo.bind("<<ComboboxSelected>>", lambda _event: self._save_daily_goal(goal_var.get()))
        self._label(goal_row, "minutes per day · builds the checklist on the Overview page", size=8, color=COLORS["muted"], background=COLORS["panel"]).pack(side="left", padx=9)

        syllabus = self._card(page, padding=19)
        syllabus.grid(row=3, column=0, sticky="ew", pady=(0, 13))
        syllabus_content = syllabus.content  # type: ignore[attr-defined]
        self._label(syllabus_content, "Official syllabus references", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(syllabus_content, "The app is independent of Kerala PSC. The linked notices define the study blueprints used here; verify the latest post-specific notification before an exam.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(5, 10))
        for track in TRACKS.values():
            row = tk.Frame(syllabus_content, bg=COLORS["panel"])
            row.pack(fill="x", pady=3)
            self._label(row, track.name, size=9, bold=True, background=COLORS["panel"]).pack(side="left")
            self._button(row, "Open official syllabus", lambda url=track.official_url: self._open_url(url), compact=True).pack(side="right")
        for label, url in CURRENT_AFFAIRS_SOURCES:
            self._button(syllabus_content, label, lambda target=url: self._open_url(target), compact=True).pack(side="left", padx=(0, 6), pady=(9, 0))

        profile_card = self._card(page, padding=19)
        profile_card.grid(row=4, column=0, sticky="ew", pady=(0, 13))
        profile_content = profile_card.content  # type: ignore[attr-defined]
        self._label(profile_content, "Local data & privacy", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(profile_content, f"Profile file: {self.store.path}\nScores, flashcards and imported packs are stored on this device. There is no sign-in, tracking, cloud sync or API key.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900, justify="left").pack(anchor="w", pady=(5, 10))
        self._button(profile_content, "Reset all local progress", self._reset_progress).pack(anchor="w")

        update_card = self._card(page, padding=19)
        update_card.grid(row=5, column=0, sticky="ew", pady=(0, 13))
        update_content = update_card.content  # type: ignore[attr-defined]
        self._label(update_content, "Install or update the Windows app", size=14, bold=True, background=COLORS["panel"]).pack(anchor="w")
        self._label(update_content, "The latest setup updates the existing install using the same installer ID. Run it over the old version; your scores and flashcards stay in your user profile.", size=9, color=COLORS["muted"], background=COLORS["panel"], wrap=900).pack(anchor="w", pady=(5, 9))
        self._button(update_content, "Get latest installer", lambda: self._open_url(LATEST_RELEASE_URL), primary=True).pack(anchor="w")

        self._label(page, "Question content is an original starter set for practice, not an official question bank or a past-paper archive. Practice helps identify gaps but cannot guarantee a score or selection.", size=8, color=COLORS["muted"], wrap=900).grid(row=6, column=0, sticky="w", pady=(0, 22))

    def _save_daily_goal(self, value: str) -> None:
        try:
            self.profile["settings"]["daily_goal_minutes"] = max(10, min(240, int(value)))
            self._save_profile()
        except ValueError:
            messagebox.showerror(APP_TITLE, "Choose a valid daily goal.")

    def _import_question_pack(self) -> None:
        path = filedialog.askopenfilename(
            title="Import an original practice question pack",
            filetypes=(("JSON question pack", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            imported = load_question_pack(path)
            existing = list(self.profile.get("custom_questions", []))
            existing_ids = {str(question.get("id", "")) for question in existing}
            built_in_ids = {question["id"] for question in self.question_pool}
            collisions = [question["id"] for question in imported if question["id"] in existing_ids or question["id"] in built_in_ids]
            if collisions:
                raise QuestionPackError("These question IDs already exist: " + ", ".join(collisions[:8]))
            updated_custom = [*existing, *imported]
            new_pool = build_question_pool(updated_custom)
        except (QuestionPackError, OSError, ValueError) as exc:
            messagebox.showerror("Question pack not imported", str(exc))
            return
        self.profile["custom_questions"] = updated_custom
        self.question_pool = new_pool
        self._save_profile()
        messagebox.showinfo(APP_TITLE, f"Imported {len(imported)} question(s). They are saved locally and available in practice and mock exams.")
        if self.current_page in {"practice", "settings"}:
            self.show_page(self.current_page)

    def _export_backup(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export progress backup",
            defaultextension=".json",
            initialfile="kerala-psc-coach-backup.json",
            filetypes=(("JSON backup", "*.json"),),
        )
        if not path:
            return
        try:
            self.store.export_backup(self.profile, path)
            messagebox.showinfo(APP_TITLE, "Your progress and imported question packs were exported.")
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not export the backup.\n\n{exc}")

    def _export_flashcards(self) -> None:
        cards = self.profile.get("flashcards", [])
        if not cards:
            messagebox.showinfo(APP_TITLE, "There are no flashcards to export yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Export flashcards as CSV",
            defaultextension=".csv",
            initialfile="kerala-psc-flashcards.csv",
            filetypes=(("CSV file", "*.csv"),),
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(("Question", "Answer", "Explanation", "Subject", "Topic", "Next review"))
                for card in cards:
                    writer.writerow((
                        card.get("question", ""),
                        card.get("answer", ""),
                        card.get("explanation", ""),
                        DOMAIN_LABELS.get(card.get("domain", ""), card.get("domain", "")),
                        card.get("topic", ""),
                        card.get("next_review", ""),
                    ))
            messagebox.showinfo(APP_TITLE, f"Exported {len(cards)} flashcard(s).")
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not export flashcards.\n\n{exc}")

    def _reset_progress(self) -> None:
        if not messagebox.askyesno(APP_TITLE, "This permanently removes local scores, flashcards and imported questions. Continue?"):
            return
        self.profile = default_profile()
        self.current_track = self.profile["settings"]["track"]
        self.question_pool = build_question_pool()
        self.last_result = None
        self._save_profile()
        self.show_page("home")



def launch() -> None:
    """Start the desktop application."""
    app = PSCCoachApp()
    app.mainloop()
