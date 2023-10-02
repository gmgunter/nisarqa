from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import replace
from fractions import Fraction
from typing import Optional, overload

import h5py
import matplotlib as mpl
import matplotlib.colors as colors
import numpy as np
import numpy.typing as npt
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter

import nisarqa

# List of objects from the import statements that
# should not be included when importing this module
objects_to_skip = nisarqa.get_all(name=__name__)


def make_hsi_browse_wrapped(
    product: nisarqa.WrappedGroup,
    params: nisarqa.HSIImageParamGroup,
    browse_png: str | os.PathLike,
) -> None:
    """
    Create and save HSI wrapped interferogram browse PNG for input product.

    Parameters
    ----------
    product : nisarqa.WrappedGroup
        Input NISAR product.
    params : nisarqa.HSIImageParamGroup
        A structure containing the parameters for creating the HSI image.
    browse_png : path-like
        Filename (with path) for the browse image PNG.
    """
    freq, pol = product.get_browse_freq_pol()

    with product.get_wrapped_igram(
        freq=freq, pol=pol
    ) as igram_r, product.get_wrapped_coh_mag(freq=freq, pol=pol) as coh_r:
        rgb_img, _ = make_hsi_raster(
            phs_or_complex_raster=igram_r,
            coh_raster=coh_r,
            equalize=params.equalize_browse,
            rewrap=None,
            longest_side_max=params.longest_side_max,
        )

    nisarqa.rslc.plot_to_rgb_png(
        red=rgb_img.data[:, :, 0],
        green=rgb_img.data[:, :, 1],
        blue=rgb_img.data[:, :, 2],
        filepath=browse_png,
    )


def make_hsi_browse_unwrapped(
    product: nisarqa.UnwrappedGroup,
    params: nisarqa.UNWHSIImageParamGroup,
    browse_png: str | os.PathLike,
) -> None:
    """
    Create and save HSI unwrapped phase image browse png for input product.

    Parameters
    ----------
    product : nisarqa.UnwrappedGroup
        Input NISAR product.
    params : nisarqa.UNWHSIImageParamGroup
        A structure containing the parameters for creating the HSI image.
    browse_png : path-like
        Filename (with path) for the browse image PNG.
    """
    freq, pol = product.get_browse_freq_pol()

    with product.get_unwrapped_phase(
        freq=freq, pol=pol
    ) as phs_r, product.get_unwrapped_coh_mag(freq=freq, pol=pol) as coh_r:
        rgb_img, _ = make_hsi_raster(
            phs_or_complex_raster=phs_r,
            coh_raster=coh_r,
            equalize=params.equalize_browse,
            rewrap=params.rewrap,
            longest_side_max=params.longest_side_max,
        )
    nisarqa.rslc.plot_to_rgb_png(
        red=rgb_img.data[:, :, 0],
        green=rgb_img.data[:, :, 1],
        blue=rgb_img.data[:, :, 2],
        filepath=browse_png,
    )


def hsi_images_to_pdf_wrapped(
    product: nisarqa.WrappedGroup,
    report_pdf: PdfPages,
) -> None:
    """
    Create HSI wrapped interferogram images and save to PDF.

    Parameters
    ----------
    product : nisarqa.WrappedGroup
        Input NISAR product.
    report_pdf : PdfPages
        The output PDF file to append the HSI image plot to.
    """
    for freq in product.freqs:
        for pol in product.get_pols(freq=freq):
            with product.get_wrapped_igram(
                freq=freq, pol=pol
            ) as igram_r, product.get_wrapped_coh_mag(
                freq=freq, pol=pol
            ) as coh_r:
                # Create a *Raster with the HSI image

                # The HSI colorbar generated in the HSI PDF function (below)
                # has a linear scale from [0, 1] for the intensity channel
                # (coherence magnitude layer). If we equalize that channel,
                # then the colorbar scale would be inaccurate.
                # So, ensure equalize=False when creating the HSI Raster.
                rgb_img, cbar_min_max = make_hsi_raster(
                    phs_or_complex_raster=igram_r,
                    coh_raster=coh_r,
                    equalize=False,  # Do not equalize the PDF HSI images
                    rewrap=None,
                    longest_side_max=None,  # Unnecessary for the PDF
                )

            save_hsi_img_to_pdf(
                img=rgb_img,
                report_pdf=report_pdf,
                cbar_min_max=cbar_min_max,
                plot_title_prefix="Wrapped Phase Image and Coherence Magnitude",
            )


def hsi_images_to_pdf_unwrapped(
    product: nisarqa.UnwrappedGroup,
    report_pdf: PdfPages,
    rewrap: Optional[float | int] = None,
) -> None:
    """
    Create HSI unwrapped phase images and save to PDF.

    Parameters
    ----------
    product : nisarqa.UnwrappedGroup
        Input NISAR product.
    report_pdf : PdfPages
        The output PDF file to append the HSI image plot to.
    rewrap : float or int or None, optional
        The multiple of pi to rewrap the unwrapped phase image when generating
        the HSI image(s). If None, no rewrapping will occur.
        Ex: If 3 is provided, the image is rewrapped to the interval [0, 3pi).
    """
    for freq in product.freqs:
        for pol in product.get_pols(freq=freq):
            with product.get_unwrapped_phase(
                freq=freq, pol=pol
            ) as phs_r, product.get_unwrapped_coh_mag(
                freq=freq, pol=pol
            ) as coh_r:
                # The HSI colorbar generated in the HSI PDF function (below)
                # has a linear scale from [0, 1] for the intensity channel
                # (coherence magnitude layer). If we equalize that channel,
                # then the colorbar scale would be inaccurate.
                # So, ensure equalize=False when creating the HSI Raster.
                rgb_img, cbar_min_max = make_hsi_raster(
                    phs_or_complex_raster=phs_r,
                    coh_raster=coh_r,
                    equalize=False,  # Do not equalize the PDF HSI images
                    rewrap=rewrap,
                    longest_side_max=None,  # Unnecessary for the PDF
                )

            save_hsi_img_to_pdf(
                img=rgb_img,
                report_pdf=report_pdf,
                cbar_min_max=cbar_min_max,
                plot_title_prefix=(
                    "Unwrapped Phase Image and Coherence Magnitude"
                ),
            )


def save_hsi_img_to_pdf(
    img: nisarqa.SARRaster,
    report_pdf: PdfPages,
    cbar_min_max: Optional[Sequence[float]] = None,
    plot_title_prefix: str = "Phase Image and Coherence Magnitude as HSI Image",
) -> None:
    """
    Annotate and save an HSI Image to PDF.

    `img.data` should be in linear.

    Parameters
    ----------
    img : *Raster
        Image in RGB color space to be saved. All image correction,
        multilooking, etc. needs to have previously been applied.
    report_pdf : PdfPages
        The output PDF file to append the HSI image plot to.
    cbar_min_max : pair of float or None, optional
        The range for the Hue axis of the HSI colorbar for the image raster.
        `None` to use the min and max of the image for the colorbar range.
        Defaults to None.
    plot_title_prefix : str, optional
        Prefix for the title of the backscatter plots.
        Defaults to "Phase Image and Coherence Magnitude as HSI Image".
    """
    # Plot and Save HSI Image to graphical summary pdf
    title = f"{plot_title_prefix}\n{img.name}"

    nisarqa.img2pdf_hsi(
        img_arr=img.data,
        title=title,
        ylim=img.y_axis_limits,
        xlim=img.x_axis_limits,
        cbar_min_max=cbar_min_max,
        xlabel=img.x_axis_label,
        ylabel=img.y_axis_label,
        plots_pdf=report_pdf,
    )


def make_hsi_as_rgb_img(
    phase_img: np.ndarray,
    coh_mag: np.ndarray,
    phs_img_range: Optional[Sequence[float | int]] = None,
    equalize: bool = False,
) -> np.ndarray:
    """
    Create HSI interferogram image array, returned in RGB colorspace.

    The phase image and coherence magnitude rasters are first processed into
    the HSI (Hue, Saturation, Intensity) colorspace, which is then converted
    to RGB values in normalized range [0, 1].

    If any input layer was NaN-valued for a given pixel, then the output
    value for that pixel will be NaN (for all channels).

    TODO: This algorithm currently uses the built-in matplotlib.hsv_to_rgb()
    to convert to RGB due to delivery schedule constraints.
    But, there is a subtle mathematical difference between the HSI and HSV
    colorspaces, and we should definitely use HSI (not HSV).
    This will require a custom implementation of HSI->RGB.

    Parameters
    ----------
    phase_img : numpy.ndarray
        2D array of a phase image (e.g. `unwrappedInterferogram`).
        This should contain real-valued pixels; if your raster is a complex
        valued interferogram, please compute the phase (e.g. use np.angle())
        and then pass in the resultant raster for `phase_img`.
    coh_mag : numpy.ndarray
        2D raster of `coherenceMagnitude` layer corresponding to `phase_img`.
        This should already be normalized to range [0, 1]. (Otherwise
        something must have gone rather wrong in the InSAR processing!)
    phs_img_range : pair of float or None, optional
        The expected range for the phase image raster. `None` to use the
        min and max of the image data. This will be used for normalization
        of the data to range [0, 1].
        Note: If `phs_img`'s data is within a known range, it is strongly
        suggested to set this parameter, otherwise unintended image correction
        will occur.
        For example, if an image was generated via np.angle(), the known range
        is [-pi, pi]. But if the actual image data only contains values from
        [-pi/2, pi/3] and `None` was provided, then the phase image will appear
        "stretched", because during normalization -pi/2 -> 0 and pi/3 -> 1.
        Defaults to None.
    equalize : bool, optional
        True to perform histogram equalization on the Intensity channel
        (the coherence magnitude layer) for the HSI image.
        See: https://scikit-image.org/docs/stable/auto_examples/color_exposure/plot_equalize.html
        Default is False.

    Returns
    -------
    rgb : numpy.ndarray
        3D array of HSI image converted to the RGB (Red Green Blue) colorspace.
        This RGB array is ready for plotting in e.g. matplotlib.
    """
    if not np.issubdtype(phase_img.dtype, np.floating):
        raise TypeError(
            f"`phase_img` has type {type(phase_img)}, must be float. "
            "Hint: If complex, perhaps compute numpy.angle(phase_img) "
            "before passing in the array."
        )

    if phase_img.ndim != 2:
        raise ValueError(
            f"`phase_img` has shape {np.shape(phase_img)}"
            "but must be a 2D array."
        )

    if coh_mag.ndim != 2:
        raise ValueError(
            f"`coh_mag` has shape {np.shape(coh_mag)} but must be a 2D array."
        )

    if np.shape(phase_img) != np.shape(coh_mag):
        raise ValueError(
            f"`phase_img` (shape: {np.shape(phase_img)}) and `coh_mag` "
            f"(shape: {np.shape(coh_mag)}) must have the same shape."
        )

    # coh mag should already be within range [0, 1].
    if np.any(coh_mag < 0.0) or np.any(coh_mag > 1.0):
        raise ValueError("`coh_mag` contains values outside of range [0, 1].")

    # Initialize HSI array
    # Note: per hsv_to_rgb(): "All values assumed to be in range [0, 1]".
    # So, we'll need to normalize all rasters added to this array.
    hsi = np.ones((phase_img.shape[0], phase_img.shape[1], 3), dtype=np.float32)

    # First channel is hue. The phase image should be represented by hue.
    # Note: If available, make sure to specify the known min/max range for
    # the image, such as [-pi, pi] for images created with np.angle().
    # Otherwise, `nisarqa.normalize()` will take the min and max of the actual
    # data, which could have the undesirable effect of applying image
    # correction to e.g. phase images.
    hsi[:, :, 0] = nisarqa.normalize(arr=phase_img, min_max=phs_img_range)

    # Second channel is saturation. We set it to 1 always.
    # Note: Nothing more to do --> It was previously initialized to 1.

    # Third channel is intensity scaled between 0, 1.
    # If the user desires, equalize histogram
    if equalize:
        # image_histogram_equalization handles normalization
        hsi[:, :, 2] = image_histogram_equalization(image=coh_mag)
    else:
        # coh mag is already within range [0, 1].
        hsi[:, :, 2] = coh_mag

    # The input arrays may contain some nan values.
    # But, we need to set them to zero for generating the HSI array.
    # So, create a temporary mask of all NaN pixels, do the computation,
    # and then set those pixels back to NaN for the final image.

    # nan_mask: True where pixels are non-finite, False where pixels are finite
    nan_mask = ~np.isfinite(phase_img) | ~np.isfinite(coh_mag)

    # For the HSI-> RGB conversion, replace all non-finite values with 0
    hsi[nan_mask] = 0.0

    # For plotting the image, convert to RGB color space
    # TODO - We need to use HSI not HSV. There is a subtle mathematical
    # difference between the two colorspaces.
    # However, this will require a custom implementation of HSI->RGB.
    rgb = colors.hsv_to_rgb(hsi)

    # Restore the NaN values
    rgb[nan_mask] = np.nan

    return rgb


@overload
def make_hsi_raster(
    phs_or_complex_raster: nisarqa.RadarRaster,
    coh_raster: nisarqa.RadarRaster,
    equalize: bool,
    rewrap: Optional[float] = None,
    longest_side_max: Optional[int] = None,
) -> tuple[nisarqa.RadarRaster, list[float, float]]:
    ...


@overload
def make_hsi_raster(
    phs_or_complex_raster: nisarqa.GeoRaster,
    coh_raster: nisarqa.GeoRaster,
    equalize: bool,
    rewrap: Optional[float] = None,
    longest_side_max: Optional[int] = None,
) -> tuple[nisarqa.GeoRaster, list[float, float]]:
    ...


def make_hsi_raster(
    phs_or_complex_raster,
    coh_raster,
    equalize,
    rewrap=None,
    longest_side_max=None,
):
    """
    Create HSI interferogram *Raster with square pixels, and colorbar range.

    Parameters
    ----------
    phs_or_complex_raster : nisarqa.GeoRaster | nisarqa.RadarRaster
        *Raster of complex interferogram or unwrapped phase data to use to
        construct the Hue layer for the HSI *Raster.
        If *Raster is complex valued, numpy.angle() will be used to compute
        the phase image (float-valued).
        This should correspond to `coh_raster`.
    coh_raster : nisarqa.GeoRaster | nisarqa.RadarRaster
        *Raster for the coherence magnitude raster to use to construct
        the intesity layer for the HSI *Raster.
        This should correspond to `phs_or_complex_raster`.
    equalize : bool, optional
        True to perform histogram equalization on the Intensity channel
        (the coherence magnitude layer) for the HSI image.
        See: https://scikit-image.org/docs/stable/auto_examples/color_exposure/plot_equalize.html
        Default is False.
    rewrap : float or int or None, optional
        The multiple of pi to rewrap the unwrapped phase image when generating
        the HSI image(s). If None, no rewrapping will occur.
        Ex: If 3 is provided, the image is rewrapped to the interval [0, 3pi).
    longest_side_max : int or None, optional
        Decimate the generated HSI raster so that the max length of
        axis 0 and axis 1 in `hsi_raster` is `longest_side_max`.

    Returns
    -------
    hsi_raster : nisarqa.GeoRaster | nisarqa.RadarRaster
        A *Raster of the HSI image converted to RGB color space. This raster
        will have square pixels. (If the rasters in `phs_or_complex_raster` and
        `coh_raster` do not have square pixels, then decimation will be applied
        to achieve square pixels.)
        The type of `hsi_raster` will be the same as the type of
        `phs_or_complex_raster` and `coh_raster`.
    cbar_min_max : pair of float
        The suggested range to use for the Hue axis of the
        HSI colorbar for `hsi_raster`.
        If `phs_or_complex_raster` has complex valued data, then `cbar_min_max`
        will be the range [-pi, +pi].
    """
    # Validate input rasters
    nisarqa.compare_raster_metadata(phs_or_complex_raster, coh_raster)

    phs_img = phs_or_complex_raster.data[...]

    if np.issubdtype(phs_img.dtype, np.complexfloating):
        # complex data; take the phase angle.
        phs_img = np.angle(phs_img.data)

        # np.angle() returns output in range [-pi, pi]
        # So, set the colobar's min and max to be the range [-pi, +pi].
        cbar_min_max = [-np.pi, np.pi]

        # Helpful hint for user!
        if rewrap is not None:
            raise RuntimeWarning(
                "Input raster has a complex dtype (implying a wrapped"
                f" interferogram), but input parameter {rewrap=}. `rewrap` is"
                " only used in the case of real-valued data (implying an"
                " unwrapped phase image). Please check that this is intended."
            )

    else:
        # unwrapped phase image
        if rewrap is None:
            # TODO - look into adding a "percentile_for_clipping" option
            cbar_min_max = [
                np.nanmin(phs_img),
                np.nanmax(phs_img),
            ]
        else:
            # `rewrap` is a multiple of pi. Convert to the full float value.
            rewrap_final = rewrap * np.pi

            # The sign of the output of the modulo operator
            # is the same as the sign of `rewrap_final`.
            # This means that it will always put the output
            # into range [0, <rewrap_final>]
            phs_img %= rewrap_final
            cbar_min_max = [0, rewrap_final]

    coh_img = coh_raster.data[...]

    rgb = nisarqa.make_hsi_as_rgb_img(
        phase_img=phs_img,
        coh_mag=coh_img,
        phs_img_range=cbar_min_max,
        equalize=equalize,
    )

    # Square the pixels. Decimate if requested.
    y_axis_spacing = phs_or_complex_raster.y_axis_spacing
    x_axis_spacing = phs_or_complex_raster.x_axis_spacing

    if longest_side_max is None:
        # Update to be the longest side of the array. This way no downsizing
        # of the image will occur, but we can still output square pixels.
        longest_side_max = max(np.shape(rgb)[:2])

    ky, kx = nisarqa.compute_square_pixel_nlooks(
        img_shape=np.shape(rgb)[:2],  # only need the x and y dimensions
        sample_spacing=[y_axis_spacing, x_axis_spacing],
        longest_side_max=longest_side_max,
    )
    rgb = rgb[::ky, ::kx]

    # Update the ground spacing so that the new *Raster we are building will
    # have correct metadata.
    y_axis_spacing = y_axis_spacing * ky
    x_axis_spacing = x_axis_spacing * kx

    # Construct the name
    # (Remove the layer name from the `name`)
    name = "_".join(phs_or_complex_raster.name.split("_")[:-1])
    if rewrap:
        pi_unicode = "\u03c0"
        name += f" - rewrapped to [0, {rewrap}{pi_unicode})"

    # Construct the HSI *Raster object
    if isinstance(phs_or_complex_raster, nisarqa.RadarRaster):
        hsi_raster = replace(
            phs_or_complex_raster,
            data=rgb,
            name=name,
            ground_az_spacing=y_axis_spacing,
            ground_range_spacing=x_axis_spacing,
        )
    elif isinstance(phs_or_complex_raster, nisarqa.GeoRaster):
        hsi_raster = replace(
            phs_or_complex_raster,
            data=rgb,
            name=name,
            y_spacing=y_axis_spacing,
            x_spacing=x_axis_spacing,
        )
    else:
        raise TypeError(
            f"Input rasters have type {type(phs_img)}, but must be either"
            " nisarqa.RadarRaster or nisarqa.GeoRaster."
        )

    return hsi_raster, cbar_min_max


def img2pdf_hsi(
    img_arr: npt.ArrayLike,
    plots_pdf: PdfPages,
    cbar_min_max: Optional[Sequence[float]] = None,
    title: Optional[str] = None,
    xlim: Optional[Sequence[float | int]] = None,
    ylim: Optional[Sequence[float | int]] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
) -> None:
    """
    Plot image array with a linear HSI "colorbar", then append to PDF.

    Parameters
    ----------
    img_arr : array_like
        Image to plot; image should represent an HSI (Hue,
        Saturation, Intensity) image that has been already converted to
        RGB colorspace (such as via matplotlib.colors.hsv_to_rgb()).
    plots_pdf : PdfPages
        The output PDF file to append the HSI image plot to.
    cbar_min_max : pair of float or None, optional
        The range for the Hue axis of the HSI colorbar for the image raster.
        `None` to use the min and max of the image data for the colorbar range.
        Defaults to None.
    title : str, optional
        The full title for the plot.
    xlim, ylim : sequence of numeric, optional
        Lower and upper limits for the axes ticks for the plot.
        Format: xlim=[<x-axis lower limit>, <x-axis upper limit>]
                ylim=[<y-axis lower limit>, <y-axis upper limit>]
    xlabel, ylabel : str, optional
        Axes labels for the x-axis and y-axis (respectively).
    """
    fig = plt.figure(constrained_layout=True)

    if title is not None:
        fig.suptitle(title)

    # Create two subplots; one to hold the actual raster image, the second
    # (smaller one) for the HSI "colorbar".
    # (Use add_subplot() to force the colorbar to be tall and skinny.)
    ax = fig.add_gridspec(5, 6)
    ax1 = fig.add_subplot(ax[:, :-2])
    ax2 = fig.add_subplot(ax[1:4, -1])

    # Set all NaN pixels to 1 in each of the red-green-blue layers.
    # This way, the NaN pixels will appear white in the PDF.
    img_to_plot = img_arr.copy()
    img_to_plot[~np.isfinite(img_arr)] = 1

    # Decimate image to a size that fits on the axes without interpolation
    # and without making the size (in MB) of the PDF explode.
    img_to_plot = decimate_img_to_size_of_axes(ax=ax1, arr=img_to_plot)

    # Plot the raster image and label it
    ax1.imshow(img_to_plot, aspect="equal", cmap="hsv", interpolation="none")

    # There are two subplots, and we want the main plot title to appear
    # over both subplots (aka centered in the figure). So, do not supply
    # the title here, otherwise the main plot title will only be centered
    # over `ax1``. (The main plot title was set above, via `fig.suptitle()`.)
    nisarqa.rslc.format_axes_ticks_and_labels(
        ax=ax1,
        img_arr_shape=np.shape(img_to_plot),
        xlim=xlim,
        ylim=ylim,
        xlabel=xlabel,
        ylabel=ylabel,
    )

    # Create the HSI "colorbar" (which is actually a subplot)
    v, h = np.mgrid[0:1:100j, 0:1:300j]
    s = np.ones_like(v)
    hsv = np.dstack((h, s, v))
    rgb = colors.hsv_to_rgb(hsv)
    rgb = np.rot90(rgb, k=3)
    rgb = np.fliplr(rgb)

    if cbar_min_max is None:
        cbar_max = np.nanmax(img_arr)
        cbar_min = np.nanmin(img_arr)

    else:
        if (len(cbar_min_max) != 2) or (cbar_min_max[0] >= cbar_min_max[1]):
            raise ValueError(
                f"{cbar_min_max=}, must be a pair of increasing values."
            )
        cbar_max = cbar_min_max[1]
        cbar_min = cbar_min_max[0]

    ax2.imshow(
        rgb,
        origin="lower",
        extent=[0, 1, cbar_min, cbar_max],
    )
    ax2.set_xlabel("InSAR\nCoherence\nMagnitude", fontsize=8.5)
    ax2.set_ylabel("InSAR Phase", fontsize=8.5, rotation=270, labelpad=10)
    ax2.yaxis.set_label_position("right")

    # If the colorbar range covers an even multiple of pi, then re-format
    # the ticks marks to look nice.
    if (np.abs(cbar_max - cbar_min) % np.pi) < 1e-6:
        # Compute number of ticks
        tick_vals = np.arange(cbar_min, cbar_max + np.pi, np.pi)

        # Only pretty-format if there are a small-ish number of ticks
        # If support for a higher number is desired, then add'l code will
        # need to be written to decimate `tick_vals` appropriately.
        if len(tick_vals) < 9:
            ax2.set_yticks(tick_vals)
            ax2.yaxis.set_major_formatter(
                FuncFormatter(
                    lambda val, pos: (
                        f"{Fraction(f'{val/np.pi:.2f}')}$\pi$"
                        if val != 0
                        else "0"
                    )
                )
            )

    ax2.yaxis.tick_right()

    ax2.set_title("HSI Color Space\nSaturation=1", fontsize=8.5)

    # Append figure to the output PDF
    plots_pdf.savefig(fig)

    # Close the plot
    plt.close(fig)


def decimate_img_to_size_of_axes(ax: mpl.Axes, arr: np.ndarray) -> np.ndarray:
    """
    Decimate array to size of axes for use with `interpolation='none'`.

    In matplotlib, setting `interpolation='none'` is useful for creating crisp
    images in e.g. output PDFs. However, when an image array is very large,
    this setting causes the generated plots (and the PDFs they're saved to)
    to be very large in size (potentially several hundred MB).

    This function is designed to decimate a large image array to have X and Y
    dimensions appropriate for the size of the given axes object.
    It maintains the same aspect ratio as the source image array.

    Parameters
    ----------
    ax : matplotlib.Axes
        Axes object. The window extent and other properties of this axes
        will be used to compute the decimation factor for the image array.
    arr : numpy.ndarray
        The (image) array to be decimated.

    Returns
    -------
    out_arr : numpy.ndarry
        Copy of `arr` that has been decimated along the first two dimensions
        so that the number of pixels in the X and Y dimensions
        approximately fits "nicely" in the window extent of the given axes.
        If the image is smaller than the axes, no decimation will occur.

    See Also
    --------
    nisarqa.compute_square_pixel_nlooks : Function to compute the decimation
        strides for an image array; until `decimate_img_to_size_of_axes()`,
        this function also accounts for making the pixels "square".
    """
    fig = ax.get_figure()

    # Get size of ax1 window in inches
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())

    height, width = np.shape(arr)[:2]
    if height >= width:
        # In this conditional, the image is taller than it is wide.
        # So, we'll want to "shrink" the image to the height of the axis.
        # (Multiply by fig.dpi to convert from inches to pixels.)
        desired_longest = bbox.height * fig.dpi

        if desired_longest <= height:
            # array is smaller than the window extent. No decimation needed.
            return arr

        # Use floor division. (Better to have resolution that is *slightly*
        # better than the axes size, rather than the image being too small
        # and needing to re-stretch it bigger to the size of the axes.)
        stride = int(height / desired_longest)
    else:
        # In this conditional, the image is shorter than it is tall.
        # So,  we'll want to "shrink" the image to the width of the axis.
        # (Multiply by fig.dpi to convert from inches to pixels.)
        desired_longest = bbox.width * fig.dpi

        if desired_longest <= width:
            # array is smaller than the window extent. No decimation needed.
            return arr

        # Use floor division. See explanation above.)
        stride = int(width / desired_longest)

    # Decimate to the correct size along the X and Y directions.
    return arr[::stride, ::stride]


def image_histogram_equalization(
    image: np.ndarray, nbins: int = 256
) -> np.ndarray:
    """
    Perform histogram equalization of a grayscale image.

    Parameters
    ----------
    image : numpy.ndarray
        N-dimensional image array. All dimensions will be combined when
        computing the histogram.
    nbins : int, optional
        Number of bins for computing the histogram.
        Defaults to 256.

    Returns
    -------
    equalized_img : numpy.ndarray
        The image with histogram equalization applied.
        This image will be in range [0, 1].

    References
    ----------
    Adapted from: skimage.exposure.equalize_hist
    Description of histogram equalization:
    https://scikit-image.org/docs/stable/auto_examples/color_exposure/plot_equalize.html
    """
    # Do not include NaN values
    img = image[np.isfinite(image)]

    hist, bin_edges = np.histogram(img.flatten(), bins=nbins, range=None)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    cdf = hist.cumsum()
    cdf = cdf / float(cdf[-1])

    out = np.interp(image.flatten(), bin_centers, cdf)
    out = out.reshape(image.shape)

    # Sanity Check. Mathematically, the output should be within range [0, 1].
    assert np.all(
        (0.0 <= out[np.isfinite(out)]) & (out[np.isfinite(out)] <= 1.0)
    ), "`out` contains values outside of range [0, 1]."

    # Unfortunately, np.interp currently always promotes to float64, so we
    # have to cast back to single precision when float32 output is desired
    return out.astype(image.dtype, copy=False)


def process_single_side_by_side_offsets_plot(
    az_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    rg_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    report_pdf: PdfPages,
) -> None:
    """
    Create and append a side-by-side plot of azimuth and range offsets to PDF.

    The colorbar interval is determined by the maximum offset value in
    either raster, and then centered at zero. This way the side-by-side plots
    will be plotted with the same colorbar scale.

    Parameters
    ----------
    az_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Along track offset layer to be processed. Must correspond to
        `rg_offset`.
    rg_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Slant range offset layer to be processed. Must correspond to
        `az_offset`.
    params : nisarqa.QuiverParamGroup
        A structure containing processing parameters to generate quiver plots.
    report_pdf : PdfPages
        The output PDF file to append the quiver plot to.
    """
    # Validate that the pertinent metadata in the rasters is equal.
    nisarqa.compare_raster_metadata(az_offset, rg_offset)

    az_img = az_offset.data[...]
    rg_img = rg_offset.data[...]

    # Compute the colorbar interval, centered around zero.
    # Both plots should use the larger of the intervals.
    # TODO - Geoff, should this be computed on the full input array?
    # or should we wait to compute it below, using the decimated array? Thanks!
    az_max = max(np.abs(np.nanmax(az_img)), np.nanmin(az_img))
    rg_max = max(np.abs(np.nanmax(rg_img)), np.nanmin(rg_img))
    cbar_max = max(az_max, rg_max)
    cbar_min = -cbar_max  # center around zero

    # Decimate to square pixels. (az and rng rasters have the same metadata)
    ky, kx = nisarqa.compute_square_pixel_nlooks(
        # only need the x and y dimensions
        img_shape=np.shape(az_img)[:2],
        sample_spacing=[az_offset.y_axis_spacing, az_offset.x_axis_spacing],
        # Only make square pixels. Use `max()` to not "shrink" the rasters.
        longest_side_max=max(np.shape(az_img)[:2]),
    )
    az_img = az_img[::ky, ::kx]
    rg_img = rg_img[::ky, ::kx]

    # Create figure and add the rasters.
    fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, constrained_layout="tight")
    fig.suptitle("Along Track and Slant Range Offsets (in meters)")

    # Decimate Along Track Offset raster and plot on left (ax1)
    az_img = decimate_img_to_size_of_axes(ax=ax1, arr=az_img)
    ax1.imshow(
        az_img,
        aspect="equal",
        cmap="magma",
        interpolation="none",
        vmin=cbar_min,
        vmax=cbar_max,
    )

    # Form axes title. (Split raster's name onto a new line to look nicer.)
    raster_name = az_offset.name.split("_")[-1]
    axes_title = az_offset.name.replace(f"_{raster_name}", f"\n{raster_name}")
    nisarqa.rslc.format_axes_ticks_and_labels(
        ax=ax1,
        img_arr_shape=np.shape(az_img),
        xlim=az_offset.x_axis_limits,
        ylim=az_offset.y_axis_limits,
        xlabel=az_offset.x_axis_label,
        ylabel=az_offset.y_axis_label,
        title=axes_title,
    )

    # Decimate slant range Offset raster and plot on right (ax2)
    rg_img = decimate_img_to_size_of_axes(ax=ax2, arr=rg_img)
    im2 = ax2.imshow(
        rg_img,
        aspect="equal",
        cmap="magma",
        interpolation="none",
        vmin=cbar_min,
        vmax=cbar_max,
    )
    # Form axes title. (Split raster's name onto a new line to look nicer.)
    raster_name = rg_offset.name.split("_")[-1]
    axes_title = rg_offset.name.replace(f"_{raster_name}", f"\n{raster_name}")
    nisarqa.rslc.format_axes_ticks_and_labels(
        ax=ax2,
        img_arr_shape=np.shape(rg_img),
        xlim=rg_offset.x_axis_limits,
        ylim=rg_offset.y_axis_limits,
        xlabel=rg_offset.x_axis_label,
        ylabel=rg_offset.y_axis_label,
        title=axes_title,
    )

    # To save space on the PDF page, we can take advantage of the fact that
    # the two rasters have the same X and Y limits and the same colorbar.
    # First, hide the y-axis labels+ticks from the right plot:
    ax2.get_yaxis().set_visible(False)
    # Second, add the colorbar to only the right plot:
    fig.colorbar(im2, ax=ax2, label="Displacement (m)")

    # Save complete plots to graphical summary PDF file
    report_pdf.savefig(fig)

    # Close figure
    plt.close(fig)


def process_az_and_range_combo_plots(
    product: nisarqa.OffsetProduct,
    params: nisarqa.QuiverParamGroup,
    report_pdf: PdfPages,
    stats_h5: h5py.File,
    browse_png: str | os.PathLike,
):
    """
    Process side-by-side az and range offsets plots and quiver plots.

    This function takes each pair of along track offset and slant range offset
    raster layers, and does three things with them:
        * Plots them side-by-side and appends this plot to PDF
        * Plots them as a quiver plot and appends this plot to PDF
        * Saves the browse image quiver plot as a PNG.
            - (The specific freq+pol+layer_number to use for the browse image
               is determined by the input `product`.)

    Parameters
    ----------
    product : nisarqa.OffsetProduct
        Input NISAR product.
    params : nisarqa.QuiverParamGroup
        A structure containing processing parameters to generate quiver plots.
    report_pdf : PdfPages
        The output pdf file to append the quiver plot to.
    stats_h5 : h5py.File
        The output file to save QA metrics, etc. to.
    browse_png : path-like
        Filename (with path) for the browse image PNG.
    """
    browse_freq, browse_pol, browse_layer_num = (
        product.get_browse_freq_pol_layer()
    )

    for freq in product.freqs:
        for pol in product.get_pols(freq):
            for layer_num in product.available_layers:
                with product.get_along_track_offset(
                    freq=freq, pol=pol, layer_num=layer_num
                ) as az_off, product.get_slant_range_offset(
                    freq=freq, pol=pol, layer_num=layer_num
                ) as rg_off:
                    # First, create the canonical side-by-side plot of the
                    # along track offsets vs. the slant range offsets.
                    process_single_side_by_side_offsets_plot(
                        az_offset=az_off,
                        rg_offset=rg_off,
                        report_pdf=report_pdf,
                    )

                    # Second, create the quiver plots. (And the browse image.)

                    process_single_quiver_plot_to_pdf(
                        az_offset=az_off,
                        rg_offset=rg_off,
                        params=params,
                        report_pdf=report_pdf,
                    )

                    # Only generate a browse PNG for one layer
                    if (
                        (layer_num == browse_layer_num)
                        and (pol == browse_pol)
                        and (freq == browse_freq)
                    ):
                        y_dec, x_dec = process_single_quiver_plot_to_png(
                            az_offset=az_off,
                            rg_offset=rg_off,
                            params=params,
                            browse_png=browse_png,
                        )

                        nisarqa.create_dataset_in_h5group(
                            h5_file=stats_h5,
                            grp_path=nisarqa.STATS_H5_QA_PROCESSING_GROUP
                            % product.band,
                            ds_name="browseDecimation",
                            ds_data=[y_dec, x_dec],
                            ds_units="unitless",
                            ds_description=(
                                "Decimation strides for the browse image."
                                " Format: [<y decimation>, <x decimation>]."
                            ),
                        )

                # # Add final colorbar range for this freq+pol+layer to stats.h5
                # # (This was a processing parameter in the YAML, so we should
                # # add it to the PDF. However, when dynamically computed,
                # # this range is not consistent between the numbered layers.
                # name = (
                #     f"quiverPlotColorbarRangeFrequency{freq}"
                #     f"Polarization{pol}Layer{layer_num}"
                # )
                # nisarqa.create_dataset_in_h5group(
                #     h5_file=stats_h5,
                #     grp_path=nisarqa.STATS_H5_QA_PROCESSING_GROUP
                #     % product.band,
                #     ds_name=name,
                #     ds_data=(cbar_min, cbar_max),
                #     ds_units="meters",
                #     ds_description=(
                #         "Colorbar range for the slant range and along track"
                #         " offset layers' quiver plot(s)."
                #     ),
                # )


def process_single_quiver_plot_to_pdf(
    az_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    rg_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    params: nisarqa.QuiverParamGroup,
    report_pdf: PdfPages,
) -> (float, float, int, int):
    """
    Process and save a single quiver plot to PDF and (optional) PNG.

    Parameters
    ----------
    az_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Along track offset layer to be processed. Must correspond to
        `rg_offset`.
    rg_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Slant range offset layer to be processed. Must correspond to
        `az_offset`.
    params : nisarqa.QuiverParamGroup
        A structure containing processing parameters to generate quiver plots.
    report_pdf : PdfPages
        The output PDF file to append the quiver plot to.

    Returns
    -------
    cbar_min, cbar_max : float
        The vmin and vmax (respectively) used for the colorbar and clipping
        the pixel offset displacement image.
    y_dec, x_dec : int
        The decimation stride value used in the Y axis direction and X axis
        direction (respectively).

    Notes
    -----
    TODO - This function needs to be better modularized to take advantage of
    existing code for plotting to PNG and PDF. It would be ideal if this
    function could follow a similar design as
    `nisarqa.rslc.process_backscatter_imgs_and_browse()`.
    However, it is tricky to extract the final quiver plot
    from the pyplot.figure() instance and return it as an RGB array.
    Let's open an issue modularize this after that release.
    """
    # Validate input rasters
    nisarqa.compare_raster_metadata(az_offset, rg_offset)

    az_off = az_offset.data[...]
    rg_off = rg_offset.data[...]

    # Create correct aspect ratio via decimation. (only need to do this on
    # one raster because az and rng rasters have the same basic metadata.)
    ky, kx = nisarqa.compute_square_pixel_nlooks(
        # only need the x and y dimensions
        img_shape=np.shape(az_off)[:2],
        sample_spacing=[az_offset.y_axis_spacing, az_offset.x_axis_spacing],
        # Only make square pixels. Use `max()` to not "shrink" the rasters.
        longest_side_max=max(np.shape(az_off)[:2]),
    )
    az_off = az_off[::ky, ::kx]
    rg_off = rg_off[::ky, ::kx]

    # Grab the axes window extent size, and decimate array to correct size for
    # plotting to the PDF
    fig, ax = plt.subplots(ncols=1, nrows=1, constrained_layout="tight")

    # Form the plot title (Remove the layer name from the layer's `name`)
    # Because of the constrained layout (which optimizes for all Artists in
    # the Figure), let's add the title before decimating the rasters.
    title = (
        f"Pixel Offset in meters\n{'_'.join(az_offset.name.split('_')[:-1])}"
    )
    fig.suptitle(title)

    az_off = decimate_img_to_size_of_axes(ax=ax, arr=az_off)
    rg_off = decimate_img_to_size_of_axes(ax=ax, arr=rg_off)

    # Create the colorful background image of the plot
    disp = np.sqrt(rg_off**2 + az_off**2)

    # Compute the vmin and vmax for the colorbar range
    # Note: because we're getting `cbar_min_max` from the `params`, the values
    # have already been validated. No further checks needed.
    # TODO - Geoff, should the vmin, vmiax be computed prior to decimation?
    cbar_min_max = params.cbar_min_max
    if cbar_min_max is None:
        # Dynamically compute the colorbar interval to be [0, max].
        # (`disp` represents magnitude, so it only contains positive values)
        vmin, vmax = 0, np.nanmax(disp)
    else:
        vmin, vmax = cbar_min_max

    # Truncate the magma cmap to only use the top half of the magma colormap
    # Adapted from: https://stackoverflow.com/a/18926541
    def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=-1):
        if (minval < 0.0) or (maxval > 1.0):
            raise ValueError(
                f"{minval=} and {maxval=}, but must be in range [0.0, 1.0]."
            )
        if n == -1:
            n = cmap.N
        new_cmap = colors.LinearSegmentedColormap.from_list(
            "trunc({name},{a:.2f},{b:.2f})".format(
                name=cmap.name, a=minval, b=maxval
            ),
            cmap(np.linspace(minval, maxval, n)),
        )
        return new_cmap

    # Use interval from [0.5, 1.0] to truncate to the top half of the magma
    # colormap range. (We do not want to use the very-dark lower half
    # for these quiver plots.)
    # Definitions: the colormap range is different than the colorbar range.
    # Colorbar range refers to the range of tick label values, while the
    # colormap determines the mapping of those values to actual visual colors.
    magma_cmap = truncate_colormap(plt.get_cmap("magma"), 0.5, 1.0)

    # Add the background image to the axes
    im = ax.imshow(
        disp, vmin=vmin, vmax=vmax, cmap=magma_cmap, interpolation="none"
    )

    # Now, prepare and add the quiver plot arrows to the axes
    arrow_stride = int(max(np.shape(disp)) / params.arrow_density)

    # Only plot the arrows at the requested strides.
    y_arrow_tip = az_off[::arrow_stride, ::arrow_stride]
    x_arrow_tip = rg_off[::arrow_stride, ::arrow_stride]

    x = np.linspace(0, x_arrow_tip.shape[1] - 1, x_arrow_tip.shape[1])
    y = np.linspace(0, x_arrow_tip.shape[0] - 1, x_arrow_tip.shape[0])
    X, Y = np.meshgrid(x, y)

    # Add the quiver arrows to the plot.
    # Multiply the start and end points for each arrow by the decimation factor;
    # this is to ensure that each arrow is placed on the correct pixel on
    # the full-resolution `disp` background image.
    ax.quiver(
        # starting x coordinate for each arrow
        X * arrow_stride,
        # starting y coordinate for each arrow
        Y * arrow_stride,
        # ending x direction component of for each arrow vector
        x_arrow_tip * arrow_stride,
        # ending y direction component of for each arrow vector
        y_arrow_tip * arrow_stride,
        angles="xy",
        scale_units="xy",
        # Use a scale less that 1 to exaggerate the arrows.
        scale=params.arrow_scaling,
        color="b",
    )

    # Add a colorbar to the figure
    cbar = fig.colorbar(im)
    cbar.ax.set_ylabel(ylabel="Displacement (m)", rotation=270, labelpad=8.0)

    nisarqa.rslc.format_axes_ticks_and_labels(
        ax=ax,
        xlim=az_offset.x_axis_limits,
        ylim=az_offset.y_axis_limits,
        img_arr_shape=np.shape(disp),
        xlabel=az_offset.x_axis_label,
        ylabel=az_offset.y_axis_label,
    )

    # Make sure axes labels do not get cut off
    # fig.tight_layout()

    # Append figure to the output PDF
    report_pdf.savefig(fig)

    # Close the plot
    plt.close(fig)


def process_single_quiver_plot_to_png(
    az_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    rg_offset: nisarqa.RadarRaster | nisarqa.GeoRaster,
    params: nisarqa.QuiverParamGroup,
    browse_png: Optional[str | os.PathLike] = None,
) -> None:
    """
    Process and save a single quiver plot to PDF and (optional) PNG.

    Parameters
    ----------
    az_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Along track offset layer to be processed. Must correspond to
        `rg_offset`.
    rg_offset : nisarqa.RadarRaster or nisarqa.GeoRaster
        Slant range offset layer to be processed. Must correspond to
        `az_offset`.
    params : nisarqa.QuiverParamGroup
        A structure containing processing parameters to generate quiver plots.
    browse_png : path-like or None, optional
        Filename (with path) for the browse image PNG.
        If None, no browse PNG will be saved. Defaults to None.
    """
    # Validate input rasters
    nisarqa.compare_raster_metadata(az_offset, rg_offset)

    # Compute decimation values for the browse image PNG.
    if (az_offset.freq == "A") and (params.decimation_freqa is not None):
        y_decimation, x_decimation = params.decimation_freqa
    elif (az_offset.freq == "B") and (params.decimation_freqb is not None):
        y_decimation, x_decimation = params.decimation_freqb
    else:
        # Square the pixels. Decimate if needed to stay within longest side max.
        longest_side_max = params.longest_side_max

        if longest_side_max is None:
            # Update to be the longest side of the array. This way no downsizing
            # of the image will occur, but we can still output square pixels.
            longest_side_max = max(np.shape(rg_offset.data))

        y_decimation, x_decimation = nisarqa.compute_square_pixel_nlooks(
            img_shape=np.shape(az_offset.data),
            sample_spacing=[az_offset.y_axis_spacing, az_offset.x_axis_spacing],
            longest_side_max=longest_side_max,
        )

    # Grab the datasets into arrays in memory.
    # While doing this, convert to square pixels and the correct size.
    az_off = az_offset.data[::y_decimation, ::x_decimation]
    rg_off = rg_offset.data[::y_decimation, ::x_decimation]

    # Use the full resolution image as the colorful background image of the plot
    disp = np.sqrt(rg_off**2 + az_off**2)

    # Compute the vmin and vmax for the colorbar range
    # Note: because we're getting `cbar_min_max` from the `params`, the values
    # have already been validated. No further checks needed.
    cbar_min_max = params.cbar_min_max
    if cbar_min_max is None:
        # Dynamically compute the colorbar interval to be [0, max].
        # (`disp` represents magnitude, so it only contains positive values)
        vmin, vmax = 0, np.nanmax(disp)
    else:
        vmin, vmax = cbar_min_max

    # Truncate the magma cmap to only use the top half of the magma colormap
    # Adapted from: https://stackoverflow.com/a/18926541
    def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=-1):
        if (minval < 0.0) or (maxval > 1.0):
            raise ValueError(
                f"{minval=} and {maxval=}, but must be in range [0.0, 1.0]."
            )
        if n == -1:
            n = cmap.N
        new_cmap = colors.LinearSegmentedColormap.from_list(
            "trunc({name},{a:.2f},{b:.2f})".format(
                name=cmap.name, a=minval, b=maxval
            ),
            cmap(np.linspace(minval, maxval, n)),
        )
        return new_cmap

    # Use interval from [0.5, 1.0] to truncate to the top half of the magma
    # colormap range. (We do not want to use the very-dark lower half
    # for these quiver plots.)
    # Definitions: the colormap range is different than the colorbar range.
    # Colorbar range refers to the range of tick label values, while the
    # colormap determines the mapping of those values to actual visual colors.
    magma_cmap = truncate_colormap(plt.get_cmap("magma"), 0.5, 1.0)

    # Make the axes size the exact size of the image dimensions.
    print("desired shape of output browse PNG: ", np.shape(disp))
    dpi = 100
    ax_height_inches = np.shape(disp)[0] / dpi
    ax_width_inches = np.shape(disp)[1] / dpi
    fig, ax = plt.subplots(figsize=(ax_height_inches, ax_width_inches), dpi=dpi)
    # fig, ax = plt.subplots()

    # Add the background image to the axes
    ax.imshow(disp, vmin=vmin, vmax=vmax, cmap=magma_cmap, interpolation="none")

    # cbar = fig.colorbar(im)
    # Now, prepare and add the quiver plot arrows to the axes
    arrow_stride = int(max(np.shape(disp)) / params.arrow_density)

    # Only plot the arrows at the requested strides.
    y_arrow_tip = az_off[::arrow_stride, ::arrow_stride]
    x_arrow_tip = rg_off[::arrow_stride, ::arrow_stride]

    x = np.linspace(0, x_arrow_tip.shape[1] - 1, x_arrow_tip.shape[1])
    y = np.linspace(0, x_arrow_tip.shape[0] - 1, x_arrow_tip.shape[0])
    X, Y = np.meshgrid(x, y)

    # Add the quiver arrows to the plot.
    # Multiply the start and end points for each arrow by the decimation factor;
    # this is to ensure that each arrow is placed on the correct pixel on
    # the full-resolution `disp` background image.
    ax.quiver(
        # starting x coordinate for each arrow
        X * arrow_stride,
        # starting y coordinate for each arrow
        Y * arrow_stride,
        # ending x direction component of for each arrow vector
        x_arrow_tip * arrow_stride,
        # ending y direction component of for each arrow vector
        y_arrow_tip * arrow_stride,
        angles="xy",
        scale_units="xy",
        # Use a scale less that 1 to exaggerate the arrows.
        scale=params.arrow_scaling,
        color="b",
    )

    # Plot to PNG
    plt.axis("off")
    fig.savefig(browse_png, bbox_inches="tight", transparent=True, pad_inches=0)

    # Close the plot
    plt.close(fig)

    return y_decimation, x_decimation


__all__ = nisarqa.get_all(__name__, objects_to_skip)
