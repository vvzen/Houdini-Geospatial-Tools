use std::io::Write;
use std::path::PathBuf;

use clap::Parser;
use color_eyre::eyre::{self, Context};
use color_eyre::owo_colors::OwoColorize;

use gdal_dtm_exporter_lib::export_dtm_to_exr;

#[derive(Parser)]
#[command(version, about)]
struct Cli {
    /// Input path pointing to the Digital Terrain Model file
    #[arg(short, long)]
    input_dtm: PathBuf,

    /// Output directory where the OpenEXR file will be exported
    #[arg(short, long)]
    output_dir: PathBuf,

    /// Normalizes the pixel values to be in the [0, 1] range.
    #[arg(short, long)]
    normalize: bool,

    /// Always override the output image if it already exists.
    #[arg(short, long)]
    yes: bool,

    /// This can be used to lower memory consumption.
    /// Higher values will result in the CLI using smaller windows
    /// when accessing the data of the DTM, while a value of 1 will read
    /// the entire image at once.
    #[arg(short, long, default_value_t = 10)]
    window_scale_factor: usize,
}

fn main() -> eyre::Result<()> {
    // Install the error handlers by eyre
    color_eyre::install()?;

    // Enable Log info by default, unless the client has other preferences
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }

    env_logger::builder()
        .format(|buf, record| {
            let style = match record.level() {
                log::Level::Warn => color_eyre::owo_colors::Style::new().yellow(),
                log::Level::Error => color_eyre::owo_colors::Style::new().bold().red(),
                _ => color_eyre::owo_colors::Style::new().white(),
            };

            writeln!(
                buf,
                "| {} | {}",
                record.level().style(style),
                record.args().style(style)
            )
        })
        .init();

    let args = Cli::parse();
    let export_dir = args.output_dir;
    let in_image_path = args.input_dtm;

    let output_image_path = export_dtm_to_exr(
        &in_image_path,
        &export_dir,
        args.window_scale_factor,
        args.yes,
        args.normalize,
    )
    .context("Failed to export OpenEXR image")?;

    log::info!("Image written to {}", output_image_path.display());

    Ok(())
}
