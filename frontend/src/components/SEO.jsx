import { Helmet } from 'react-helmet-async'
import { useLocation } from 'react-router-dom'

const DEFAULT = {
  title: 'TrappistAI - Generate AI Images, Music & 3D Models with CSPR',
  description:
    'TrappistAI is a multi-modal AI generation platform powered by Casper blockchain. Create images, music, 3D models and chat with AI. Pay with CSPR tokens.',
  keywords:
    'TrappistAI, AI generation, Casper blockchain, CSPR, generate images, generate music, 3D models, crypto AI, artificial intelligence, x402 payments',
  image: 'https://trappist.land/trappist1.png',
}

export default function SEO({
  title = DEFAULT.title,
  description = DEFAULT.description,
  keywords = DEFAULT.keywords,
  image = DEFAULT.image,
  noindex = false,
}) {
  const location = useLocation()
  const canonical = `https://trappist.land${location.pathname}`

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <meta name="robots" content={noindex ? 'noindex, nofollow' : 'index, follow'} />
      <link rel="canonical" href={canonical} />

      <meta property="og:type" content="website" />
      <meta property="og:url" content={canonical} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:url" content={canonical} />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />
    </Helmet>
  )
}
