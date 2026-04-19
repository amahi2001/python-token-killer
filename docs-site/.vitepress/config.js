import { defineConfig } from 'vitepress'
import llmstxt from 'vitepress-plugin-llms'

export default defineConfig({
  title: 'ptk — python-token-killer',
  description: 'Stop paying for nulls. Token compression for Python LLM workflows.',
  base: '/python-token-killer/',

  vite: {
    plugins: [
      llmstxt({
        domain: 'https://amahi2001.github.io/python-token-killer/',
        generateLLMsFullTxt: true,
      }),
    ],
  },

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'API Reference', link: '/api/reference' },
      {
        text: 'GitHub',
        link: 'https://github.com/amahi2001/python-token-killer',
      },
      {
        text: 'PyPI',
        link: 'https://pypi.org/project/python-token-killer/',
      },
    ],

    sidebar: [
      {
        text: 'Getting Started',
        items: [{ text: 'Installation & First Use', link: '/guide/getting-started' }],
      },
      {
        text: 'Core Functions',
        items: [
          { text: 'ptk / minimize / stats / detect_type', link: '/api/reference' },
        ],
      },
      {
        text: 'Use Cases',
        items: [{ text: 'RAG, LangChain/LangGraph, CI Logs, Diffs', link: '/guide/use-cases' }],
      },
      {
        text: 'Contributing',
        items: [
          {
            text: 'Contributing Guide',
            link: 'https://github.com/amahi2001/python-token-killer/blob/main/CONTRIBUTING.md',
          },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/amahi2001/python-token-killer' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024 amahi2001',
    },
  },
})
