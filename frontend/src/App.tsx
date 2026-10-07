import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import './App.css'
import {
  Activity,
  ArrowUpRight,
  Bell,
  Bot,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Command,
  Database,
  FileText,
  FolderKanban,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { McBadge } from '@/components/ui/mc-badge'
import { McButton } from '@/components/ui/mc-button'
import { McCard, McCardContent, McCardFooter, McCardHeader } from '@/components/ui/mc-card'
import { McProgress, McProgressTrack } from '@/components/ui/mc-progress'

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Projects', icon: FolderKanban },
  { label: 'Datasets', icon: Database },
  { label: 'Team', icon: Users },
]

const projects = [
  { name: 'MCDI Auth', type: 'Backend service', status: 'Active', updated: '2 min ago', color: 'violet', progress: 78 },
  { name: 'Campus Assistant', type: 'AI workspace', status: 'In review', updated: 'Yesterday', color: 'blue', progress: 52 },
  { name: 'Event analytics', type: 'Data project', status: 'Active', updated: '3 days ago', color: 'orange', progress: 91 },
]

function App() {
  const [active, setActive] = useState('Overview')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [dark, setDark] = useState(true)

  const filteredProjects = useMemo(
    () => projects.filter((project) => project.name.toLowerCase().includes(query.toLowerCase())),
    [query],
  )

  return (
    <div className={dark ? 'app-shell dark' : 'app-shell'}>
      <aside className={mobileOpen ? 'sidebar sidebar-open' : 'sidebar'}>
        <div className="brand-row">
          <div className="brand-mark"><Sparkles size={18} /></div>
          <div><strong>multAI</strong><span>MicroClub workspace</span></div>
          <McButton aria-label="Close navigation" variant="tertiary" size="sm" icon="only" onClick={() => setMobileOpen(false)} className="mobile-close"><X /></McButton>
        </div>
        <div className="workspace-switcher"><div className="workspace-avatar">M</div><div><span>Workspace</span><strong>MicroClub USTHB</strong></div><ChevronDown size={15} /></div>
        <nav aria-label="Main navigation" className="nav-list">
          <p className="nav-label">Workspace</p>
          {navItems.map((item) => {
            const Icon = item.icon
            return <button className={active === item.label ? 'nav-item active' : 'nav-item'} key={item.label} onClick={() => { setActive(item.label); setMobileOpen(false) }}><Icon size={17} /><span>{item.label}</span>{item.label === 'Projects' && <McBadge size="sm">3</McBadge>}</button>
          })}
          <p className="nav-label nav-label-spaced">Manage</p>
          <button className="nav-item" onClick={() => setActive('Activity')}><Activity size={17} /><span>Activity</span></button>
          <button className="nav-item" onClick={() => setActive('Settings')}><Settings size={17} /><span>Settings</span></button>
        </nav>
        <div className="sidebar-bottom"><div className="help-card"><CircleHelp size={17} /><div><strong>Need a hand?</strong><span>Read the docs</span></div><ArrowUpRight size={14} /></div><div className="user-row"><div className="user-avatar">AK</div><div><strong>Amine K.</strong><span>Administrator</span></div><MoreHorizontal size={17} /></div></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><McButton aria-label="Open navigation" variant="tertiary" size="sm" icon="only" className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu /></McButton><div className="crumb"><span>Workspace</span><ChevronRight size={14} /><strong>{active}</strong></div><div className="top-actions"><div className="search-wrap"><Search size={16} /><input aria-label="Search projects" placeholder="Search" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>⌘ K</kbd></div><McButton aria-label="Notifications" variant="tertiary" size="sm" icon="only"><Bell /></McButton><div className="top-avatar">AK</div></div></header>

        <div className="page-wrap">
          <section className="hero"><div><div className="eyebrow"><span className="status-dot" /> Tuesday, October 7, 2026</div><h1>Good morning, Amine.</h1><p>Here&apos;s what&apos;s happening across your workspace today.</p></div><div className="hero-actions"><McButton variant="secondary" size="md" icon="leading"><FileText />View reports</McButton><McButton variant="primary" size="md" icon="leading" onClick={() => setActive('Projects')}><Plus />New project</McButton></div></section>

          <section className="stats-grid" aria-label="Workspace metrics"><StatCard icon={<FolderKanban />} label="Total projects" value="12" change="+2 this month" /><StatCard icon={<Bot />} label="AI requests" value="8,429" change="+18.2% vs last month" /><StatCard icon={<Users />} label="Team members" value="24" change="+4 new members" /><StatCard icon={<TrendingUp />} label="Success rate" value="98.6%" change="+1.4% this month" /></section>

          <section className="content-grid"><McCard className="projects-card"><McCardHeader title="Recent projects" description="Your latest work across multAI." /><McCardContent><div className="table-head"><span>Project</span><span>Status</span><span>Last updated</span><span /></div>{filteredProjects.map((project) => <div className="project-row" key={project.name}><div className={`project-icon ${project.color}`}><FolderKanban size={17} /></div><div className="project-name"><strong>{project.name}</strong><span>{project.type}</span><div className="row-progress"><McProgress value={project.progress}><McProgressTrack /></McProgress><small>{project.progress}%</small></div></div><McBadge variant={project.status === 'Active' ? 'default' : 'secondary'} size="sm">{project.status}</McBadge><span className="updated"><Clock3 size={14} />{project.updated}</span><McButton aria-label={`Open ${project.name}`} variant="tertiary" size="sm" icon="only"><MoreHorizontal /></McButton></div>)}</McCardContent><McCardFooter align="end"><McButton variant="link" size="sm" icon="trailing">View all projects <ArrowUpRight /></McButton></McCardFooter></McCard>
            <div className="side-stack"><McCard className="usage-card"><McCardHeader title="Monthly usage" description="Your workspace consumption." /><McCardContent><div className="usage-value"><strong>68%</strong><McBadge variant="secondary" size="sm" icon={<TrendingUp />}>On track</McBadge></div><McProgress value={68}><McProgressTrack /></McProgress><div className="usage-foot"><span>6,824 / 10,000 requests</span><span>Resets in 12 days</span></div></McCardContent><McCardFooter><McButton variant="secondary" size="sm" icon="trailing">Manage plan <ArrowUpRight /></McButton></McCardFooter></McCard><McCard className="activity-card"><McCardHeader title="Recent activity" description="Latest workspace events." /><McCardContent><ActivityItem icon={<ShieldCheck />} title="Auth flow deployed" time="12 minutes ago" color="green" /><ActivityItem icon={<Database />} title="Dataset connected" time="1 hour ago" color="blue" /><ActivityItem icon={<Users />} title="New member joined" time="3 hours ago" color="orange" /></McCardContent></McCard></div></section>

          <section className="insight-banner"><div className="insight-icon"><Sparkles /></div><div><McBadge variant="leading" size="sm">Workspace insight</McBadge><h2>Your projects are moving faster.</h2><p>Deployment velocity is up 24% compared to last month. Keep the momentum going.</p></div><McButton variant="secondary" size="md" icon="trailing">View analytics <ArrowUpRight /></McButton></section>
          <footer className="page-footer"><span>multAI by MicroClub USTHB</span><span><Command size={13} /> Built for focused teams</span></footer>
        </div>
      </main>
      <button className="theme-toggle" aria-label="Toggle theme" onClick={() => setDark(!dark)}>{dark ? '☼' : '◐'}</button>
    </div>
  )
}

function StatCard({ icon, label, value, change }: { icon: ReactNode; label: string; value: string; change: string }) {
  return <McCard className="stat-card"><div className="stat-top"><div className="stat-icon">{icon}</div><ArrowUpRight size={15} className="muted-icon" /></div><div className="stat-value">{value}</div><div className="stat-label">{label}</div><div className="stat-change">{change}</div></McCard>
}

function ActivityItem({ icon, title, time, color }: { icon: ReactNode; title: string; time: string; color: string }) {
  return <div className="activity-item"><div className={`activity-icon ${color}`}>{icon}</div><div><strong>{title}</strong><span>{time}</span></div><ChevronRight size={14} className="muted-icon" /></div>
}

export default App
