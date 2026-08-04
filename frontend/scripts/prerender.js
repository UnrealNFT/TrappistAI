/**
 * Lightweight prerender for SEO.
 * After Vite builds the SPA, this script generates static HTML shells for
 * key routes so search engines see real content without running JavaScript.
 * React still hydrates the page client-side once loaded.
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(__dirname, '../dist')
const templatePath = path.join(dist, 'index.html')

if (!fs.existsSync(templatePath)) {
  console.error('dist/index.html not found. Run vite build first.')
  process.exit(1)
}

const template = fs.readFileSync(templatePath, 'utf-8')

const routes = {
  '/': {
    title: 'TrappistAI - AI Image, Music & 3D Generator on Casper Blockchain',
    description:
      'Generate images, music, 3D models and chat with AI on TrappistAI. Pay with CSPR tokens on Casper blockchain or via the x402 payment protocol.',
    content: `
      <h1>TrappistAI - Multi-modal AI Generation Platform</h1>
      <p>Create AI-generated images, music tracks, 3D models and chat with AI. TrappistAI is powered by the Casper blockchain and lets you pay with CSPR tokens.</p>
      <p>Developers can also use the x402 payment protocol to build programmable AI agents that pay for generations with native CSPR.</p>
      <ul>
        <li>Image generation with FLUX.1-schnell</li>
        <li>Music generation with HeartMuLa and MiniMax</li>
        <li>3D model generation with Hunyuan and Tripo3D</li>
        <li>AI chat powered by Groq</li>
      </ul>
    `,
  },
  '/generate': {
    title: 'Generate AI Images, Music & 3D Models | TrappistAI',
    description:
      'Create AI-generated images, music tracks, 3D models and chat with AI on TrappistAI. Pay with CSPR tokens or via the x402 protocol.',
    content: `
      <h1>Generate AI Content</h1>
      <p>Use TrappistAI to generate images, music, 3D models or chat with AI. Each generation costs a small amount of credits paid in CSPR on the Casper blockchain.</p>
      <p>Supports FLUX.1-schnell for images, HeartMuLa and MiniMax for music, Hunyuan and Tripo3D for 3D assets.</p>
    `,
  },
  '/buy-credits': {
    title: 'Buy AI Generation Credits with CSPR | TrappistAI',
    description:
      'Buy credits to generate images, music, 3D models and chat with AI on TrappistAI. Pay with CSPR tokens on Casper blockchain.',
    content: `
      <h1>Buy Credits with CSPR</h1>
      <p>Purchase TrappistAI credits using your Casper Wallet. Pay with native CSPR tokens and start generating images, music, 3D models and chat instantly.</p>
    `,
  },
  '/x402': {
    title: 'x402 AI Generator - Pay for AI with CSPR | TrappistAI',
    description:
      'Discover how TrappistAI uses the x402 payment protocol to let you pay for AI image, music and 3D generation with native CSPR on Casper blockchain.',
    content: `
      <h1>x402 AI Generator</h1>
      <p>TrappistAI integrates the x402 protocol so developers can pay for AI image, music and 3D generation programmatically with native CSPR tokens on the Casper blockchain.</p>
      <p>x402 turns payment into a native HTTP primitive: the server returns 402 Payment Required, the client signs a CSPR transfer, and the resource is delivered automatically.</p>
      <h2>Why x402 for AI?</h2>
      <ul>
        <li>No subscription or credit card required</li>
        <li>Native CSPR settlement on-chain</li>
        <li>Standard HTTP headers and receipt proofs</li>
        <li>Perfect for AI agents and automated workflows</li>
      </ul>
    `,
  },
}

for (const [route, data] of Object.entries(routes)) {
  let html = template
    .replace(/<title>.*?<\/title>/, `<title>${data.title}</title>`)
    .replace(/<meta name="description" content=".*?" \/>/, `<meta name="description" content="${data.description}" />`)
    .replace(
      /<meta property="og:title" content=".*?" \/>/,
      `<meta property="og:title" content="${data.title}" />`
    )
    .replace(
      /<meta property="og:description" content=".*?" \/>/,
      `<meta property="og:description" content="${data.description}" />`
    )
    .replace(
      /<meta name="twitter:title" content=".*?" \/>/,
      `<meta name="twitter:title" content="${data.title}" />`
    )
    .replace(
      /<meta name="twitter:description" content=".*?" \/>/,
      `<meta name="twitter:description" content="${data.description}" />`
    )
    .replace(
      /<link rel="canonical" href=".*?" \/>/,
      `<link rel="canonical" href="https://trappist.land${route}" />`
    )

  // Inject static content for crawlers while keeping the React root intact
  html = html.replace(
    /<div id="root"><\/div>/,
    `<div id="root"><!--seo-content-->${data.content}<!--/seo-content--></div>`
  )

  const fileName = route === '/' ? 'index.html' : `${route.slice(1)}.html`
  const outPath = path.join(dist, fileName)
  fs.writeFileSync(outPath, html)
  console.log(`Prerendered ${route} -> ${fileName}`)
}

console.log('Prerender complete.')
