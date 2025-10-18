// Routes configuration for web-analysis
// This can be imported by the host shell when using Module Federation

import App from './App'

export const routes = [
  {
    path: '/analysis',
    component: App,
  },
]

export default routes

