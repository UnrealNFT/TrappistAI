import { useEffect, useRef } from 'react'

export default function TerminalText({ messages = [] }) {
  const outputRef = useRef(null)

  useEffect(() => {
    if (!outputRef.current || messages.length === 0) return

    const output = outputRef.current
    output.innerHTML = '' // Clear previous content

    const $new = (tag) => document.createElement(tag)
    const $text = (text) => document.createTextNode(text)
    const $append = (el) => output.appendChild(el)
    const $rnd = () => Math.floor(Math.random() * 125)

    const $promise = (thenFn) => {
      let args, promise, wait
      const isResolved = false
      
      promise = {
        wait: (ms) => {
          wait = ms
          return promise
        },
        then: (...newArgs) => {
          args = newArgs
          return $promise(thenFn)
        },
        resolve: () => {
          if (args) {
            const next = () => thenFn(...args, promise)
            wait ? setTimeout(next, wait) : next()
          }
        }
      }
      return promise
    }

    const process = (target, chars, promise) => {
      const first = chars[0]
      const rest = chars.slice(1)
      
      if (!first) {
        promise.resolve()
        return
      }
      
      target.appendChild(first)
      setTimeout(() => process(target, rest, promise), $rnd())
    }

    const type = (text, promise) => {
      const chars = text.split('').map($text)
      promise = promise || $promise(type)
      
      $append($new('br'))
      const q = $new('q')
      $append(q)
      process(q, chars, promise)
      
      return promise
    }

    // Chain all messages
    let chain = type(messages[0])
    for (let i = 1; i < messages.length; i++) {
      chain = chain.wait(300).then(messages[i])
    }

  }, [messages])

  return (
    <div className="terminal-output">
      <output ref={outputRef} className="terminal-display"></output>
    </div>
  )
}
