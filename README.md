# Sheek Posh daily posts

Images for Sheek Posh's daily Facebook and Instagram posts. Each image is made in ChatGPT from a product on sheekposh.com, saved here, and scheduled through Zernio using its raw GitHub link.

This repo is public on purpose: Zernio has to be able to download the images.

## Layout

- `posts/YYYY/` holds the images, one per day.
- File name: `YYYY-MM-DD-{product-handle}.png`, e.g. `posts/2026/2026-11-16-black-premium-pashmina-shawl.png`. Shorten long handles to the first 6 words.
- `posts/log.csv` has one row per day: date, product handle, colour, background, image path, status.

Raw link format for Zernio:
`https://raw.githubusercontent.com/aqib1401/sheekposh-posts/main/posts/YYYY/{file}.png`
