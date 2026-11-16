import { useState } from "react";
import { ArrowRight, BriefcaseBusiness, ClipboardList, FileUser, Pause, Play, Radar, Sparkles, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./landing.css";

const features = [
  { icon: FileUser, title: "Give your search a starting point", text: "Upload a resume and review the skills and experience JobPilot extracts. Choose the resume you want it to match against." },
  { icon: Radar, title: "Collect jobs every morning", text: "JobPilot checks active sources at 8:00 AM IST while the backend is running. It saves eligible jobs that score above 80% against your primary resume." },
  { icon: ClipboardList, title: "Track where you’ve applied", text: "Mark a job as applied to move it from AI Matches into your Applications table." },
  { icon: Users, title: "Reach out to recruiters", text: "Browse HR contacts, choose recipients, and preview an email template before sending." },
];

const codeFragments = [
  "await collectJobs()", "score > 80", "{ resume: primary }",
  "jobs.filter(isEligible)", "match(resume, job)", "schedule('08:00 IST')",
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const [paused, setPaused] = useState(false);
  const start = user ? "/matches" : "/register";
  const startLabel = user ? "Open workspace" : "Create an account";

  return (
    <div className="landing">
      <div className="landing-ambient" data-paused={paused} aria-hidden="true">
        <i />
        <i />
        {codeFragments.map((fragment) => <span key={fragment}>{fragment}</span>)}
      </div>
      <header className="landing-header">
        <Link to="/" className="landing-brand"><Sparkles size={20} aria-hidden="true" /> JobPilot AI</Link>
        <nav aria-label="Account navigation">
          {!loading && (user ? (
            <Link to="/matches" className="landing-link">Open workspace <ArrowRight size={16} /></Link>
          ) : (
            <Link to="/login" className="landing-link">Log in <ArrowRight size={16} /></Link>
          ))}
        </nav>
      </header>

      <main className="landing-main">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-intro">
            <h1 id="landing-title">Find jobs that <em>fit your resume.</em></h1>
            <p>JobPilot collects openings, scores them against your experience, and gives you one place to track applications and reach out to recruiters.</p>
            <div className="landing-actions">
              <Link className="landing-primary" to={start}>{startLabel} <ArrowRight size={18} /></Link>
              <a className="landing-link" href="#how-it-works">How it works</a>
            </div>
          </div>

          <figure className="landing-preview" data-paused={paused} aria-label="Illustrative preview of a JobPilot match">
            <figcaption>
              <span className="landing-window-dots" aria-hidden="true"><i /><i /><i /></span>
              Example match
              <button type="button" className="landing-demo-toggle" aria-label={paused ? "Play animations" : "Pause animations"}
                onClick={() => setPaused((value) => !value)}>
                {paused ? <Play size={16} /> : <Pause size={16} />}
              </button>
            </figcaption>
            <div className="landing-demo-progress" aria-hidden="true"><i /></div>
            <div className="landing-code">
              <div><span>input</span> primary_resume.pdf</div>
              <div><span>scan</span> Career pages · Telegram · Job feeds</div>
              <div><span>filter</span> Match score &gt; 80%</div>
              <div className="landing-code-result"><span>result</span> Match ready <i aria-hidden="true" /></div>
            </div>
            <div className="landing-result">
              <div className="landing-result-icon"><BriefcaseBusiness size={22} aria-hidden="true" /></div>
              <div><strong>Frontend Engineer</strong><small>Example role · Remote in India</small></div>
              <strong className="landing-score">94%</strong>
            </div>
          </figure>
        </section>

        <section id="how-it-works" className="landing-features" aria-labelledby="landing-features-title">
          <h2 id="landing-features-title">How JobPilot works</h2>
          <div className="landing-feature-grid">
            {features.map(({ icon: Icon, title, text }) => (
              <article key={title}>
                <Icon size={22} aria-hidden="true" />
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer className="landing-footer"><span>JobPilot AI</span><Link to={start}>{startLabel} <ArrowRight size={16} /></Link></footer>
    </div>
  );
}
