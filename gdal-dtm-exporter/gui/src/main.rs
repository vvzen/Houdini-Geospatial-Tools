#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")] // hide console window on Windows in release

use std::path::PathBuf;

use eframe::egui;
use humansize::{format_size, BINARY};

use gdal_dtm_exporter_lib::export_dtm_to_exr;

const PADDING_SIZE: f32 = 16.0;

fn main() -> Result<(), eframe::Error> {
    // Enable Log info by default, unless the client has other preferences
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }
    env_logger::init(); // Log to stderr (if you run with `RUST_LOG=debug`).

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_min_inner_size([380.0, 300.0])
            .with_inner_size([360.0, 380.0]) // wide enough for the drag-drop overlay text
            .with_drag_and_drop(true),
        ..Default::default()
    };

    eframe::run_native(
        "DTM Exporter",
        options,
        Box::new(|cc| Box::new(MyApp::new(cc))),
    )
}

enum UserAction {
    Dropped,
    Picked,
}

enum ConversionStatus {
    NotStarted,
    InProgress,
    Finished,
}

struct MyApp {
    dropped_files: Vec<egui::DroppedFile>,
    picked_path: Option<String>,
    input_file: PathBuf,
    output_dir: String,
    last_action: Option<UserAction>,
    drag_in_progress: bool,
    normalize: bool,
    overwrite_output: bool,
    window_scale_factor: f32,
    channel_tx: std::sync::mpsc::SyncSender<bool>,
    channel_rx: std::sync::mpsc::Receiver<bool>,
    conversion_status: ConversionStatus,
}

impl MyApp {
    fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let (tx, rx) = std::sync::mpsc::sync_channel(1);

        Self {
            dropped_files: Vec::new(),
            picked_path: None,
            last_action: None,
            drag_in_progress: false,
            normalize: true,
            overwrite_output: true,
            window_scale_factor: 10.0,
            input_file: PathBuf::default(),
            output_dir: String::from("/tmp"),
            channel_tx: tx,
            channel_rx: rx,
            conversion_status: ConversionStatus::NotStarted,
        }
    }
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("DTM to OpenEXR Exporter");

            ui.label("Drag and drop a '.img' file in this window or click on 'Select file'");
            let input_file_dialog = rfd::FileDialog::new().add_filter(".IMG", &["IMG", "img"]);

            if ui.button("Select file").clicked() {
                if let Some(path) = input_file_dialog.pick_file() {
                    self.picked_path = Some(path.display().to_string());
                }
                self.last_action = Some(UserAction::Picked);
            }

            let output_dir_dialog = rfd::FileDialog::new();
            if ui.button("Choose output directory").clicked() {
                if let Some(path) = output_dir_dialog.pick_folder() {
                    self.output_dir = format!("{}", path.display());
                }
            }

            ui.add_space(PADDING_SIZE);

            // If the processing of the dragged files takes time,
            // give a hint to the user that we're not stuck
            ui.separator();

            match self.last_action {
                // Show picked file
                Some(UserAction::Picked) => {
                    if let Some(picked_path) = &self.picked_path {
                        ui.horizontal(|ui| {
                            ui.label("Input file:");
                            ui.monospace(picked_path);
                        });

                        ui.horizontal(|ui| {
                            if let Ok(md) = std::fs::metadata(picked_path) {
                                let bytes_hr = format_size(md.len(), BINARY);
                                ui.label(format!("File size: {} bytes", bytes_hr));
                            }
                        });

                        self.input_file = picked_path.into();
                    }
                }

                // Show dropped files (if any)
                Some(UserAction::Dropped) => {
                    // TODO: Find a nice way to shortcircuit
                    let last_file = self.dropped_files.last();

                    if let Some(file) = last_file {
                        // TODO: No unwraps
                        self.input_file = file.path.as_ref().cloned().unwrap().to_path_buf();

                        ui.group(|ui| {
                            ui.label("Dropped files:");
                            ui.label(format!("{}", self.input_file.display()));
                        });
                    }
                }
                _ => {}
            }

            if self.drag_in_progress {
                ui.horizontal(|ui| {
                    ui.label("Processing..");
                });
            }

            egui::CollapsingHeader::new("Conversion Options")
                .default_open(true)
                .show(ui, |ui| {
                    ui.label("Output directory");
                    ui.text_edit_singleline(&mut self.output_dir);

                    ui.checkbox(&mut self.normalize, "Normalize")
                        .on_hover_text("Normalizes the pixel values to be in the [0, 1] range");
                    ui.checkbox(&mut self.overwrite_output, "Override")
                        .on_hover_text("Always override the output image if it already exists");

                    ui.label("Window Scale Factor");

                    let wsf_tooltip = concat!(
                        "This can be used to lower memory consumption. ",
                        "Higher values will result in the CLI ",
                        "using smaller windows when accessing the data"
                    );

                    ui.add(egui::widgets::Slider::new(
                        &mut self.window_scale_factor,
                        1.0..=100.0,
                    ))
                    .on_hover_text(wsf_tooltip);
                });

            // Run conversion
            ui.add_space(PADDING_SIZE);

            let tx = self.channel_tx.clone();

            match self.conversion_status {
                ConversionStatus::NotStarted | ConversionStatus::Finished => {
                    let export_button = ui.button("Export to OpenEXR");

                    if export_button.clicked() {
                        log::info!("Converting {} ..", self.input_file.display());

                        let output_dir = PathBuf::from(&self.output_dir);
                        let input_file = self.input_file.clone();
                        let wsf = self.window_scale_factor.clone();
                        let overwrite_output = self.overwrite_output.clone();
                        let normalize = self.normalize.clone();

                        if !input_file.exists() {
                            ui.label(format!(
                                "Input file doesn't exist: {}",
                                input_file.display()
                            ));
                            return;
                        }

                        self.conversion_status = ConversionStatus::InProgress;

                        // Perform the conversion in a separate thread
                        std::thread::spawn(move || {
                            log::info!("Spawned thread to do the processing..");

                            let result = match export_dtm_to_exr(
                                &input_file,
                                &output_dir,
                                wsf as usize,
                                overwrite_output,
                                normalize,
                            ) {
                                Ok(v) => {
                                    log::info!("Export done to {}", v.display());
                                    true
                                }
                                Err(e) => {
                                    log::error!("{e}");
                                    false
                                }
                            };

                            log::info!("Sending from thread..");

                            if let Err(e) = tx.send(result) {
                                log::error!("Failed to send from thread: {e}");
                            }

                            log::info!("About to exit from thread..");
                        });
                    }

                    if matches!(self.conversion_status, ConversionStatus::Finished) {
                        ui.horizontal(|ui| {
                            ui.label("Conversion completed!");
                        });
                    }
                }

                ConversionStatus::InProgress => {
                    // Constantly check if it's over
                    match self.channel_rx.try_recv() {
                        Ok(stuff) => {
                            self.conversion_status = ConversionStatus::Finished;
                            log::info!("Received stuff: {stuff}");
                        }
                        Err(e) => {
                            if e != std::sync::mpsc::TryRecvError::Empty {
                                log::error!("Failed to receive from thread: {e}");
                            }
                        }
                    }

                    ui.horizontal(|ui| {
                        ui.label("Conversion in progress..");
                    });
                }
            }
        });

        preview_files_being_dropped(ctx, self);

        // Collect dropped files:
        ctx.input(|i| {
            if !i.raw.dropped_files.is_empty() {
                self.dropped_files.clone_from(&i.raw.dropped_files);
                self.last_action = Some(UserAction::Dropped);
                self.drag_in_progress = false;
            }
        });
    }
}

/// Preview hovering files:
fn preview_files_being_dropped(ctx: &egui::Context, app: &mut MyApp) {
    use egui::*;

    if !ctx.input(|i| i.raw.hovered_files.is_empty()) {
        app.drag_in_progress = true;

        let painter =
            ctx.layer_painter(LayerId::new(Order::Foreground, Id::new("file_drop_target")));

        let text = "Drop..";

        let screen_rect = ctx.screen_rect();
        painter.rect_filled(screen_rect, 0.0, Color32::from_black_alpha(192));
        painter.text(
            screen_rect.center(),
            Align2::CENTER_CENTER,
            text,
            TextStyle::Heading.resolve(&ctx.style()),
            Color32::WHITE,
        );
    }
}
