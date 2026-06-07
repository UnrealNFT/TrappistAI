import React from 'react'
import ReactDOM from 'react-dom/client'
import { ClickProvider } from '@make-software/csprclick-ui'
import { CONTENT_MODE } from '@make-software/csprclick-core-types'
import App from './App.jsx'
import './index.css'

const clickOptions = {
  appName: config.cspr_click_app_name,
  appId: config.cspr_click_app_id,
  contentMode: CONTENT_MODE.IFRAME,
  providers: config.cspr_click_providers
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ClickProvider options={clickOptions}>
      <App />
    </ClickProvider>
  </React.StrictMode>,
)
