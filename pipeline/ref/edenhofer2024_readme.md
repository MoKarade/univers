# A Parsec-Scale Galactic 3D Dust Map out to 1.25 kpc from the Sun -- Dataset for the 1.25 kpc 3D Dust Map and the 2 kpc 3D Dust Map

All data products are made publicly available.
The data products are stored in the FITS file format.
The main data products are the posterior samples of the spatial 3D distribution of dust extinction discretized to HEALPix spheres at logarithmically spaced distances.
For convenience, we also provide the posterior mean and standard deviation of the samples of the HEALPix spheres at logarithmically spaced distances.

We additionally interpolate the posterior mean and standard deviation to a Cartesian grid.
The interpolation is carried out at a lower resolution using 2³ pc³ voxels to keep the filesize reasonably small.
We recommend re-interpolating the map at a higher resolution for the study of individual regions within the map.

We release the interpolation script as part of the data release.
Its signature reads `interp2box.py [-h] [-o OUTPUT_DIRECTORY] [-b BOX] healpix_path`.
A box is a string of two tuples separated by two colons.
The first tuple specifies the number of voxels along each axis of the box and the second tuple specifies the corners of the box in parsecs in heliocentric coordinates.
To interpolate the map to a box with 1051 x 1051 x 351 voxels of size |X|, |Y| ≤ 2100 pc and |Z| ≤ 700 pc, use
`interp2box.py -b '(1051,1051,351)::((-2100,2100),(-2100,2100),(-700,700))' -- mean_and_std_healpix.fits`.

In addition, we interpolate the posterior mean and standard deviation to galactic longitude, latitude and distance.
The signature of the interpolation script reads `interp2lbd.py [-h] [-o OUTPUT_DIRECTORY] [-b BOX] healpix_path`.
Its behavior is similar to `interp2box.py` but the box is specified in terms of galactic longitude, latitude and distance in units of degrees, degrees, and parsecs respectively.

Both scripts require the Python packages numpy (Harris et al. 2020), astropy (Astropy Collaboration et al. 2013, 2018, 2022), and healpy (Górski et al. 2005; Zonca et al. 2019).
Depending on the number of output voxels, the interpolation can be very memory intensive and computationally expensive.

## Files

### Maps

The main data product is `samples_healpix.fits`.
All other data products are derived quantities.

* `samples_healpix.fits` -- main data product; posterior samples of the dust density in HEALPix times distance
* `mean_and_std_healpix.fits` -- posterior mean and std. of the dust density in HEALPix times distance
* `mean_and_std_xyz.fits` -- posterior mean and std. of the dust density interpolated to Galactic XYZ
* `mean_and_std_lbd.fits` -- posterior mean and std. of the dust density interpolated to Galactic longitude, latitude, and distance
* `stellar_extinction_catalog.fits` -- table of samples of extinction predictions and measurement error predictions per star

We additionally release an auxiliary reconstruction using less data but which extends out to 2 kpc in distance.
We advise caution when interpreting small scale features or structures at high distances in this map.

* `validation_with_less_data_but_2kpc_samples_healpix.fits` -- posterior samples of the dust density in HEALPix times distance of the auxiliary validation reconstruction using less data but which extends out to 2 kpc in distance
* `validation_with_less_data_but_2kpc_mean_and_std_healpix.fits` -- posterior mean and std. of the dust density in HEALPix times distance of the auxiliary 2 kpc reconstruction with less data
* `validation_with_less_data_but_2kpc_mean_and_std_xyz.fits` -- posterior mean and std. of the dust density interpolated to Galactic XYZ of the auxiliary 2 kpc reconstruction with less data
* `validation_with_less_data_but_2kpc_mean_and_std_lbd.fits` -- posterior mean and std. of the dust density interpolated to Galactic longitude, latitude, and distance of the auxiliary 2 kpc reconstruction with less data
* `validation_with_less_data_but_2kpc_stellar_extinction_catalog.fits` -- table of samples of extinction predictions and measurement error predictions per star of the auxiliary 2 kpc reconstruction with less data

### Scripts

* `interp2box.py` -- interpolation script to translate HEALPix times distance into Galactic XYZ
* `interp2lbd.py` -- interpolation script to translate HEALPix times distance into Galactic longitude, latitude, and distance

## Change Log

* v1.0.2 -- fix the values of the `CTYPE`s in the FITS files produced by `interp2lbd.py`
* v1.0.1 -- adapt readme.md to make the zenodo preview work, add missing `interp2box.py` and `interp2lbd.py` scripts
* v1.0 -- initial release
