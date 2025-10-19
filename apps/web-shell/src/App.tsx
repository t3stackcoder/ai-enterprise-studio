import { useState, MouseEvent } from 'react'
import './styles/theme.css'

export default function App() {
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('theme')
    return savedTheme ? savedTheme === 'dark' : true
  })
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [activeNavIndex, setActiveNavIndex] = useState<number | null>(null)
  const [chatTitle, setChatTitle] = useState('Chat')

  const navTitles = ['Video Production', 'Creative Copilot', 'Podcast Studio']

  const toggleTheme = () => {
    const newTheme = !isDark
    setIsDark(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
  }

  const createRipple = (event: MouseEvent<HTMLButtonElement>, contained = false) => {
    const button = event.currentTarget
    const circle = document.createElement('span')
    const rect = button.getBoundingClientRect()

    if (contained) {
      const size = Math.min(button.clientWidth, button.clientHeight) * 0.8
      circle.style.width = circle.style.height = `${size}px`
      circle.style.left = `${(button.clientWidth - size) / 2}px`
      circle.style.top = `${(button.clientHeight - size) / 2}px`
    } else {
      const diameter = Math.max(button.clientWidth, button.clientHeight)
      const radius = diameter / 2
      circle.style.width = circle.style.height = `${diameter}px`
      circle.style.left = `${event.clientX - rect.left - radius}px`
      circle.style.top = `${event.clientY - rect.top - radius}px`
    }

    circle.classList.add('ripple')
    if (contained) {
      circle.classList.add('contained')
    }

    const ripple = button.getElementsByClassName('ripple')[0]
    if (ripple) {
      ripple.remove()
    }

    button.appendChild(circle)

    setTimeout(() => {
      if (circle.parentNode) {
        circle.parentNode.removeChild(circle)
      }
    }, 600)
  }

  const handleNavClick = (index: number, event: MouseEvent<HTMLButtonElement>) => {
    createRipple(event)
    
    if (isSidebarOpen && activeNavIndex === index) {
      setIsSidebarOpen(false)
      setActiveNavIndex(null)
    } else {
      setActiveNavIndex(index)
      setChatTitle(navTitles[index])
      setIsSidebarOpen(true)
    }
  }

  const handleCloseSidebar = (event: MouseEvent<HTMLButtonElement>) => {
    createRipple(event, true)
    setIsSidebarOpen(false)
    setActiveNavIndex(null)
  }

  return (
    <div className={isDark ? 'dark-theme' : 'light-theme'} style={{ width: '100%', height: '100vh' }}>
      <div className="interface-container">
          {/* Chat Sidebar */}
          <div className={`chat-sidebar ${isSidebarOpen ? 'open' : ''}`}>
            <div className="chat-header">
              <h2 className="chat-title">{chatTitle}</h2>
              <div className="chat-actions">
                <button className="action-button" onMouseDown={handleCloseSidebar}>
                  <svg className="icon" style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24">
                    <path d="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z"/>
                  </svg>
                </button>
              </div>
            </div>
            <div className="chat-content">
              {/* Chat content will go here */}
            </div>
          </div>

          {/* Icon Sidebar */}
          <div className="icon-sidebar">
            {/* Teams Logo */}
            <div className="teams-logo">
              <img src="Logo.png" alt="Logo" />
            </div>
            
            {/* Navigation Icons */}
            <div className="nav-icons">
              <div className="tooltip">
                <button 
                  className={`nav-button ${activeNavIndex === 0 ? 'active' : ''}`}
                  onMouseDown={(e) => handleNavClick(0, e)}
                >
                  <svg className="icon" viewBox="0 0 24 24">
                    <path d="M17,9H7V7C7,6.45 7.45,6 8,6H16C16.55,6 17,6.45 17,7V9M18,15V9C18,7.89 17.11,7 16,7V6C16,4.89 15.11,4 14,4H10C8.89,4 8,4.89 8,6V7C6.89,7 6,7.89 6,9V15C6,16.11 6.89,17 8,17H16C17.11,17 18,16.11 18,15M22,8.5L20,10.5V8C20,7.45 19.55,7 19,7H18V15H19C19.55,15 20,14.55 20,14V11.5L22,13.5V8.5Z"/>
                  </svg>
                </button>
                <span className="tooltiptext">Video Production</span>
              </div>

              <div className="tooltip">
                <button 
                  className={`nav-button ${activeNavIndex === 1 ? 'active' : ''}`}
                  onMouseDown={(e) => handleNavClick(1, e)}
                >
                  <svg className="icon" viewBox="0 0 24 24">
                    <path d="M17.5,12A1.5,1.5 0 0,1 16,10.5A1.5,1.5 0 0,1 17.5,9A1.5,1.5 0 0,1 19,10.5A1.5,1.5 0 0,1 17.5,12M10,10.5C10,11.33 9.33,12 8.5,12C7.67,12 7,11.33 7,10.5C7,9.67 7.67,9 8.5,9C9.33,9 10,9.67 10,10.5M12,14C9.58,14 7.56,15.32 6.36,17.25H17.64C16.44,15.32 14.42,14 12,14M12,3A9,9 0 0,0 3,12A9,9 0 0,0 12,21C16.97,21 21,16.97 21,12A9,9 0 0,0 12,3M12,19C7.03,19 3,14.97 3,10C3,5.03 7.03,1 12,1C16.97,1 21,5.03 21,10C21,14.97 16.97,19 12,19Z"/>
                    <path d="M9,11H15L13,13H11V15H13L15,17H9V11Z"/>
                    <circle cx="12" cy="5.5" r="1"/>
                    <circle cx="6.5" cy="7.5" r="1"/>
                    <circle cx="17.5" cy="7.5" r="1"/>
                  </svg>
                </button>
                <span className="tooltiptext">Creative Copilot</span>
              </div>

              <div className="tooltip">
                <button 
                  className={`nav-button ${activeNavIndex === 2 ? 'active' : ''}`}
                  onMouseDown={(e) => handleNavClick(2, e)}
                >
                  <svg className="icon" viewBox="0 0 24 24">
                    <path d="M12,1C7,1 3,5 3,10V17A3,3 0 0,0 6,20H8V12H6V10A6,6 0 0,1 12,4A6,6 0 0,1 18,10V12H16V20H18A3,3 0 0,0 21,17V10C21,5 17,1 12,1Z"/>
                  </svg>
                </button>
                <span className="tooltiptext">Podcast Studio</span>
              </div>
            </div>

            {/* Theme Toggle */}
            <div className="tooltip">
              <button 
                className="theme-toggle" 
                onMouseDown={(e) => createRipple(e)}
                onClick={toggleTheme}
              >
                <svg 
                  className={`icon fade-transition ${isDark ? 'show' : ''}`} 
                  viewBox="0 0 24 24"
                >
                  <path d="M12,18C11.11,18 10.26,17.8 9.5,17.45C11.56,16.5 13,14.42 13,12C13,9.58 11.56,7.5 9.5,6.55C10.26,6.2 11.11,6 12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18M20,8.69V4H15.31L12,0.69L8.69,4H4V8.69L0.69,12L4,15.31V20H8.69L12,23.31L15.31,20H20V15.31L23.31,12L20,8.69Z"/>
                </svg>
                <svg 
                  className={`icon fade-transition ${!isDark ? 'show' : ''}`} 
                  viewBox="0 0 24 24" 
                  style={{ position: 'absolute' }}
                >
                  <path d="M12,8A4,4 0 0,0 8,12A4,4 0 0,0 12,16A4,4 0 0,0 16,12A4,4 0 0,0 12,8M12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12A6,6 0 0,1 12,18M20,8.69V4H15.31L12,0.69L8.69,4H4V8.69L0.69,12L4,15.31V20H8.69L12,23.31L15.31,20H20V15.31L23.31,12L20,8.69Z"/>
                </svg>
              </button>
              <span className="tooltiptext">Toggle light/dark mode</span>
            </div>
          </div>

          {/* Main Content Area */}
          <div className={`main-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
            <div className="top-bar">
          <div className="top-bar-title">Welcome to Mayfly</div>
        </div>
        <div className="content-body">
          {/* Main content will go here */}
        </div>
      </div>
    </div>
  </div>
  )
}
