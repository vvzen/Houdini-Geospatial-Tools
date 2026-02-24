use std::io::BufRead;
use std::ops::{Add, Div, Mul, Sub};
use std::path::PathBuf;

use color_eyre::eyre;
use gdal::{raster::ResampleAlg, Metadata};
use image::{Rgb, Rgb32FImage};

/// Map a value from one range to another
/// Taken from https://rosettacode.org/wiki/Map_range#Rust
fn map_range<T: Copy>(from_range: (T, T), to_range: (T, T), s: T) -> T
where
    T: Add<T, Output = T> + Sub<T, Output = T> + Mul<T, Output = T> + Div<T, Output = T>,
{
    to_range.0 + (s - from_range.0) * (to_range.1 - to_range.0) / (from_range.1 - from_range.0)
}

pub fn export_dtm_to_exr(
    in_image_path: &PathBuf,
    export_dir: &PathBuf,
    window_scale_factor: usize,
    force_overwrite: bool,
    normalize: bool,
) -> eyre::Result<PathBuf> {
    std::fs::DirBuilder::new()
        .recursive(true)
        .create(&export_dir)?;

    let dataset = gdal::Dataset::open(&in_image_path)?;

    // For the 2d export
    let (raster_w, raster_h) = dataset.raster_size();

    let mut output_image = Rgb32FImage::new(raster_w as u32, raster_h as u32);
    let output_image_path = export_dir
        .join(
            in_image_path
                .file_stem()
                .ok_or("Input path didn't have a file name")
                .map_err(eyre::Error::msg)?,
        )
        .with_extension("exr");

    let num_bands = dataset.raster_count();

    log::info!(
        "This {} is in '{}' and has {num_bands} band(s).",
        dataset.driver().long_name(),
        dataset
            .spatial_ref()?
            .name()
            .unwrap_or("unknown Spatial Ref".to_string())
    );

    log::info!("Raster size: {raster_w}x{raster_h}");

    // Let's try to read a small portion of this image
    // (NOTE: bands are 1-indexed)
    for i in 1..=num_bands {
        let band = dataset.rasterband(i)?;

        // Depending on the file, the description field may be the empty string :(
        let description = band.description()?;
        if !description.is_empty() {
            log::info!("\tDescription: '{description}'");
        }

        let stats = band.compute_raster_min_max(true)?;
        log::info!("Band min: {}, max: {}", stats.min, stats.max);

        log::info!("Processing image..");

        // In GDAL, all no-data values are coerced to floating point types, regardless of the
        // underlying pixel type.
        log::debug!("No-data value: {:?}", band.no_data_value());
        log::debug!("Pixel data type: {}", band.band_type());

        // How much do we read at each iteration
        let region_size_w = raster_w / window_scale_factor;
        let region_size_h = raster_h / window_scale_factor;

        // Downsampling factor (doesn't work right now, so keep it as 1)
        let resize_factor = 1;

        for x_offset in (0..raster_w).step_by(region_size_w) {
            for y_offset in (0..raster_h).step_by(region_size_h) {
                log::debug!("");

                // In GDAL you can read arbitrary regions of the raster, and have them up- or down-sampled
                // when the output buffer size is different from the read size. The terminology GDAL
                // uses takes getting used to. All parameters here are in pixel coordinates.
                // Also note, tuples are in `(x, y) / (cols, rows)` order.
                // `window` is the (x, y) coordinate of the upper left corner of the region to read.
                let window = (x_offset as isize, y_offset as isize);

                let region_to_read_w;
                let region_to_read_h;

                // Handle case where the last tile is smaller
                if x_offset >= raster_w - region_size_w {
                    region_to_read_w = raster_w - x_offset;
                } else {
                    region_to_read_w = region_size_w;
                }

                if y_offset >= raster_h - region_size_h {
                    region_to_read_h = raster_h - y_offset;
                } else {
                    region_to_read_h = region_size_h;
                }

                log::debug!("\tOffset: {x_offset}x{y_offset}");
                log::debug!("\tRegion: {region_to_read_w}x{region_to_read_h}");

                // How much we should read
                let window_size = (region_to_read_w as usize, region_to_read_h as usize);

                // `output_size` is the output buffer size. If this is different from `window_size`, then
                // the `resample_algo` parameter below becomes relevant.
                let output_size = (
                    region_to_read_w / resize_factor as usize,
                    region_to_read_h / resize_factor as usize,
                );
                let resample_algo = ResampleAlg::Bilinear;

                let rv =
                    band.read_as::<f32>(window, window_size, output_size, Some(resample_algo))?;

                log::debug!("\tData shape:   {:?}", rv.shape());
                // log::debug!("\tData values: {:?} ({})", rv.data, rv.data.len());

                // Take N at a time horizontally
                for (c, chunk) in rv.data().chunks(region_to_read_w).enumerate() {
                    let y = y_offset + c;

                    for (i, value) in chunk.iter().enumerate() {
                        let x = x_offset + i;

                        let bw_color = match normalize {
                            true => {
                                map_range((stats.min, stats.max), (0.0, 1.0), *value as f64) as f32
                            }
                            false => *value as f32,
                        };

                        output_image.put_pixel(
                            x as u32,
                            y as u32,
                            Rgb([bw_color, bw_color, bw_color]),
                        );
                    }
                }
            }
        }
    }

    log::debug!("Writing image to disk..");

    // Ask for confirmation
    if !force_overwrite && output_image_path.exists() {
        log::debug!("File exists, do you want to override it? y/n");

        let mut lock = std::io::stdin().lock();
        let mut answer = String::new();

        lock.read_line(&mut answer)?;

        let answer = match answer.strip_suffix("\n") {
            Some(v) => v,
            None => &answer,
        };

        if answer == "n" || answer == "no" {
            eyre::bail!("User decided to not override: aborting.");
        }
    }

    output_image.save(&output_image_path)?;

    Ok(output_image_path)
}
