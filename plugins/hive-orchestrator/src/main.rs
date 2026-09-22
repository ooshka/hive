use std::collections::BTreeMap;

use zellij_tile::prelude::*;

register_plugin!(State);

#[derive(Default)]
struct State {
    tabs: Vec<TabInfo>,
    panes: Option<PaneManifest>,
    permission_requested: bool,
    pending_new_agent: Option<usize>,
    pending_close_agent: Option<usize>,
}

#[derive(Clone)]
struct PaneMatch {
    tab_position: usize,
    pane_id: PaneId,
    title: String,
}

impl ZellijPlugin for State {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        set_selectable(false);
        subscribe(&[EventType::Timer, EventType::PermissionRequestResult]);
        set_timeout(0.1);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::TabUpdate(tabs) => {
                if !self.tabs.is_empty() {
                    if let Some(tab) = tabs.iter().find(|tab| {
                        tab.active
                            && is_assistant_tab(&tab.name)
                            && !self.tabs.iter().any(|known| known.tab_id == tab.tab_id)
                    }) {
                        self.pending_new_agent = Some(tab.tab_id);
                    }
                }
                self.tabs = tabs;
                self.follow_new_agent();
                false
            }
            Event::PaneUpdate(panes) => {
                self.panes = Some(panes);
                self.follow_new_agent();
                self.finish_close_agent();
                false
            }
            Event::Timer(_) => {
                if !self.permission_requested {
                    self.permission_requested = true;
                    request_permission(&[
                        PermissionType::ReadApplicationState,
                        PermissionType::ChangeApplicationState,
                        PermissionType::ReadCliPipes,
                    ]);
                    subscribe(&[EventType::TabUpdate, EventType::PaneUpdate]);
                }
                false
            }
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                set_selectable(false);
                subscribe(&[EventType::TabUpdate, EventType::PaneUpdate]);
                false
            }
            _ => false,
        }
    }

    fn pipe(&mut self, pipe_message: PipeMessage) -> bool {
        match pipe_message.name.as_str() {
            "focus-agent" => self.focus_agent(),
            "focus-editor" => self.focus_editor(),
            "focus-git" => go_to_tab_name("git"),
            "toggle-split" => self.toggle_split(),
            "close-agent" => self.close_agent(),
            _ => {}
        }
        false
    }

    fn render(&mut self, _rows: usize, _cols: usize) {}
}

impl State {
    fn close_agent(&mut self) {
        let Some(active) = self.active_assistant_tab() else {
            return;
        };
        // The oldest assistant tab is the initial session. Keep it available.
        if self.assistant_tabs().first().map(|tab| tab.tab_id) == Some(active.tab_id) {
            return;
        }
        if let Some(editor) = self.editor_pane().filter(|pane| pane.tab_position == active.position) {
            self.pending_close_agent = Some(active.tab_id);
            if let Some(edit_tab) = self.tabs.iter().find(|tab| tab.name == "edit") {
                if let Some(anchor) = self.panes_in_tab(edit_tab.position).first() {
                    stack_panes(vec![anchor.pane_id, editor.pane_id]);
                } else {
                    self.pending_close_agent = None;
                }
            } else {
                break_panes_to_new_tab(&[editor.pane_id], Some("edit".to_string()), false);
            }
        } else {
            close_tab_with_id(active.tab_id as u64);
        }
    }

    fn finish_close_agent(&mut self) {
        let Some(tab_id) = self.pending_close_agent else {
            return;
        };
        let Some(tab) = self.tabs.iter().find(|tab| tab.tab_id == tab_id) else {
            self.pending_close_agent = None;
            return;
        };
        if self.editor_pane().is_some_and(|pane| pane.tab_position == tab.position) {
            return;
        }
        self.pending_close_agent = None;
        close_tab_with_id(tab_id as u64);
    }

    fn follow_new_agent(&mut self) {
        let Some(tab_id) = self.pending_new_agent else {
            return;
        };
        let Some(tab) = self
            .active_assistant_tab()
            .filter(|tab| tab.tab_id == tab_id)
        else {
            self.pending_new_agent = None;
            return;
        };
        let Some(editor) = self.editor_pane() else {
            return;
        };
        if !self.editor_is_split(&editor) || editor.tab_position == tab.position {
            self.pending_new_agent = None;
            return;
        }
        // The new tab can arrive before its pane is created or renamed by Hive.
        let Some(agent) = self.agent_pane_in_tab(tab.position) else {
            return;
        };
        self.pending_new_agent = None;
        self.pair_editor(&editor, &tab);
        focus_pane_with_id(agent.pane_id, false, false);
    }

    fn focus_agent(&self) {
        let assistant_tabs = self.assistant_tabs();
        if assistant_tabs.is_empty() {
            go_to_tab_name("assistant-start");
            return;
        }

        let editor = self.editor_pane();
        let active = self.active_tab();
        let active_is_assistant = active
            .as_ref()
            .map(|tab| is_assistant_tab(&tab.name))
            .unwrap_or(false);

        let target = if active_is_assistant {
            let active_position = active.map(|tab| tab.position).unwrap_or(0);
            let current_index = assistant_tabs
                .iter()
                .position(|tab| tab.position == active_position)
                .unwrap_or(0);

            assistant_tabs[(current_index + 1) % assistant_tabs.len()].clone()
        } else {
            assistant_tabs[0].clone()
        };

        if let Some(editor) = editor {
            if self.editor_is_split(&editor) && editor.tab_position != target.position {
                self.pair_editor(&editor, &target);
            } else {
                go_to_tab_name(&target.name);
            }
        } else {
            go_to_tab_name(&target.name);
        }

        if let Some(agent) = self.agent_pane_in_tab(target.position) {
            focus_pane_with_id(agent.pane_id, false, false);
        }
    }

    fn focus_editor(&self) {
        if let Some(editor) = self.editor_pane() {
            focus_pane_with_id(editor.pane_id, false, false);
        } else {
            go_to_tab_name("edit");
        }
    }

    fn toggle_split(&self) {
        let Some(editor) = self.editor_pane() else {
            go_to_tab_name("edit");
            return;
        };

        if self
            .assistant_tabs()
            .iter()
            .any(|tab| tab.position == editor.tab_position)
        {
            let agent = self.agent_pane_in_tab(editor.tab_position);
            if let Some(edit_tab) = self.tabs.iter().find(|tab| tab.name == "edit") {
                if let Some(anchor) = self.panes_in_tab(edit_tab.position).first() {
                    stack_panes(vec![anchor.pane_id, editor.pane_id]);
                } else {
                    return;
                }
            } else {
                break_panes_to_new_tab(&[editor.pane_id], Some("edit".to_string()), false);
            }
            if let Some(agent) = agent {
                focus_pane_with_id(agent.pane_id, false, false);
            }
            return;
        }

        let target = self
            .active_assistant_tab()
            .or_else(|| self.assistant_tabs().into_iter().next());

        if let Some(tab) = target {
            self.pair_editor(&editor, &tab);
            focus_pane_with_id(editor.pane_id, false, false);
        } else {
            go_to_tab_name("assistant-start");
        }
    }

    fn pair_editor(&self, editor: &PaneMatch, tab: &TabInfo) {
        let Some(agent) = self.agent_pane_in_tab(tab.position) else {
            return;
        };
        // Zellij 0.44.3's break-to-existing-tab APIs mix tab IDs and positions.
        // Stacking by pane ID reliably brings the editor into the agent's tab;
        // the native swap layout immediately unstacks them into left/right panes.
        focus_pane_with_id(agent.pane_id, false, false);
        stack_panes(vec![agent.pane_id, editor.pane_id]);
        if self.panes_in_tab(tab.position).len() == 1 {
            next_swap_layout();
            move_pane_with_pane_id_in_direction(editor.pane_id, Direction::Right);
        }
    }

    fn active_tab(&self) -> Option<TabInfo> {
        self.tabs.iter().find(|tab| tab.active).cloned()
    }

    fn active_assistant_tab(&self) -> Option<TabInfo> {
        self.tabs
            .iter()
            .find(|tab| tab.active && is_assistant_tab(&tab.name))
            .cloned()
    }

    fn assistant_tabs(&self) -> Vec<TabInfo> {
        let mut tabs: Vec<_> = self
            .tabs
            .iter()
            .filter(|tab| is_assistant_tab(&tab.name))
            .cloned()
            .collect();
        tabs.sort_by_key(|tab| tab.position);
        tabs
    }

    fn editor_is_split(&self, editor: &PaneMatch) -> bool {
        self.assistant_tabs()
            .iter()
            .any(|tab| tab.position == editor.tab_position)
    }

    fn editor_pane(&self) -> Option<PaneMatch> {
        self.find_pane(|pane| is_editor_title(&pane.title))
    }

    fn agent_pane_in_tab(&self, tab_position: usize) -> Option<PaneMatch> {
        let mut panes = self.panes_in_tab(tab_position);
        panes.sort_by_key(|pane| pane.title.clone());
        panes.into_iter().find(|pane| is_agent_title(&pane.title))
    }

    fn find_pane<F>(&self, predicate: F) -> Option<PaneMatch>
    where
        F: Fn(&PaneInfo) -> bool,
    {
        for (tab_position, panes) in &self.panes.as_ref()?.panes {
            for pane in panes {
                if pane.is_plugin || pane.is_floating || pane.is_suppressed || pane.exited {
                    continue;
                }
                if predicate(pane) {
                    return Some(self.to_pane_match(*tab_position, pane));
                }
            }
        }
        None
    }

    fn panes_in_tab(&self, tab_position: usize) -> Vec<PaneMatch> {
        let Some(manifest) = &self.panes else {
            return Vec::new();
        };
        manifest
            .panes
            .get(&tab_position)
            .into_iter()
            .flatten()
            .filter(|pane| {
                !pane.is_plugin && !pane.is_floating && !pane.is_suppressed && !pane.exited
            })
            .map(|pane| self.to_pane_match(tab_position, pane))
            .collect()
    }

    fn to_pane_match(&self, tab_position: usize, pane: &PaneInfo) -> PaneMatch {
        PaneMatch {
            tab_position,
            pane_id: PaneId::Terminal(pane.id),
            title: pane.title.clone(),
        }
    }
}

fn is_assistant_tab(name: &str) -> bool {
    name == "codex" || name.starts_with("codex:") || name == "claude" || name.starts_with("claude:")
}

fn is_editor_title(title: &str) -> bool {
    title.starts_with("Editor - ")
}

fn is_agent_title(title: &str) -> bool {
    title.starts_with("Codex ")
        || title.starts_with("Codex - ")
        || title.starts_with("Claude ")
        || title.starts_with("Claude - ")
}
