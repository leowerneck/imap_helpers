# SWAPI GSE Velocities

The `proton-sw` and `alpha-sw` products report each bulk velocity in Geocentric Solar Ecliptic (GSE) coordinates as well as RTN.
The GSE velocity is computed from the Sun-frame RTN velocity $`\mathbf{v}^{\text{RTN}}`$ (`*_sw_velocity_rtn_sun`) and its covariance $`\Sigma^{\text{RTN}}`$ (`*_sw_velocity_rtn_covariance`), one epoch at a time, by `convert_sun_velocity_rtn_to_gse` in [`swapi/l3a/utils.py`](../../imap_l3_processing/swapi/l3a/utils.py#L122).
All SPICE quantities are evaluated at the ephemeris time $`t`$ of the measurement (`et`, [L143](../../imap_l3_processing/swapi/l3a/utils.py#L143)).

## Ingredients from SPICE

| Symbol | Shape | Meaning | Code |
|---|---|---|---|
| $`M`$ | $`3\times 3`$ | rotation from RTN to ECLIPJ2000 axes | `eclipj2000_from_rtn`, [L146](../../imap_l3_processing/swapi/l3a/utils.py#L146) |
| $`T`$ | $`6\times 6`$ | state transform from ECLIPJ2000 to GSE | `gse_from_eclipj2000`, [L151](../../imap_l3_processing/swapi/l3a/utils.py#L151) |
| $`\mathbf{r}_{\oplus}`$ | $`3`$ | IMAP position relative to Earth, ECLIPJ2000 [km] | `position_from_earth`, [L156](../../imap_l3_processing/swapi/l3a/utils.py#L156) |
| $`\mathbf{u}_{\oplus}`$ | $`3`$ | Earth velocity relative to the Sun, ECLIPJ2000 [km/s] | `earth_velocity_from_sun`, [L162](../../imap_l3_processing/swapi/l3a/utils.py#L162) |

GSE rotates relative to ECLIPJ2000 (its $`x`$ axis follows the Sun–Earth line), so `spiceypy.sxform` returns a state transform rather than a plain rotation:
```math
T = \begin{pmatrix} R & 0 \\ \dot{R} & R \end{pmatrix},
```
where $`R`$ is the $`3\times 3`$ ECLIPJ2000-to-GSE rotation and $`\dot{R}`$ its time derivative.

## Velocity

First rotate the measured velocity to ECLIPJ2000 axes and change the rest frame from the Sun to Earth ([L166–L167](../../imap_l3_processing/swapi/l3a/utils.py#L166)):
```math
\mathbf{v}_{\odot} = M\thinspace \mathbf{v}^{\text{RTN}}, \qquad
\mathbf{v}_{\oplus} = \mathbf{v}_{\odot} - \mathbf{u}_{\oplus}.
```
Then build the Earth-centered state of the plasma at IMAP's location, apply $`T`$, and keep the velocity half ([L169–L170](../../imap_l3_processing/swapi/l3a/utils.py#L169)):
```math
\begin{pmatrix} \mathbf{r}^{\text{GSE}} \\ \mathbf{v}^{\text{GSE}} \end{pmatrix}
= T \begin{pmatrix} \mathbf{r}_{\oplus} \\ \mathbf{v}_{\oplus} \end{pmatrix}
\quad\Longrightarrow\quad
\mathbf{v}^{\text{GSE}} = R\thinspace \mathbf{v}_{\oplus} + \dot{R}\thinspace \mathbf{r}_{\oplus}.
```
The term $`\dot{R}\thinspace\mathbf{r}_{\oplus}`$ is why the position is needed: it accounts for the rotation of the GSE axes (about one turn per year).
At IMAP's distance from Earth ($`\sim 1.5\times 10^{6}`$ km) it is $`\sim 0.3`$ km/s.

## Covariance

Writing the result in terms of the measured velocity,
```math
\mathbf{v}^{\text{GSE}} = (R M)\thinspace \mathbf{v}^{\text{RTN}} \;-\; R\thinspace\mathbf{u}_{\oplus} + \dot{R}\thinspace\mathbf{r}_{\oplus},
```
the last two terms do not depend on $`\mathbf{v}^{\text{RTN}}`$, so they shift the mean but not the spread.
The covariance therefore only sees the rotation $`G = R M`$, where $`R`$ is the lower-right block `gse_from_eclipj2000[3:, 3:]` ([L174–L175](../../imap_l3_processing/swapi/l3a/utils.py#L174)):
```math
\Sigma^{\text{GSE}} = G\thinspace \Sigma^{\text{RTN}}\thinspace G^{\top}.
```
The reported uncertainty `*_sw_velocity_gse_uncert` is $`\sqrt{\operatorname{diag}(\Sigma^{\text{GSE}})}`$, computed when the data product is written (`to_data_product_variables` in [`swapi/l3a/models.py`](../../imap_l3_processing/swapi/l3a/models.py#L172)).

## Per-epoch handling

`_add_gse_velocities` in [`swapi/swapi_processor.py`](../../imap_l3_processing/swapi/swapi_processor.py#L49) applies the conversion to every epoch after the chunk fits, for both protons and alphas:

- epochs whose Sun-frame RTN velocity is fill (NaN) are skipped and stay fill;
- if the SPICE conversion raises (e.g. missing kernel coverage), the epoch stays fill and gets the `FIT_ERROR` quality flag;
- results are stored as `{species}_sw_velocity_gse` and `{species}_sw_velocity_gse_covariance`.

## Check

`test_convert_sun_velocity_rtn_to_gse_matches_spice_state_of_imap` in [`tests/swapi/l3a/test_utils.py`](../../tests/swapi/l3a/test_utils.py#L351) feeds IMAP's own heliocentric velocity through the conversion.
It checks that the result matches IMAP's velocity in `IMAP_GSE` as reported directly by SPICE (so the $`\dot{R}\thinspace\mathbf{r}_{\oplus}`$ term is included), and that the covariance equals $`G\thinspace\Sigma^{\text{RTN}}\thinspace G^{\top}`$.
