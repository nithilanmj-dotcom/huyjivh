import { useEffect, useMemo, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Award,
  Bell,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Compass,
  Dumbbell,
  Flame,
  Footprints,
  Gift,
  Heart,
  Home,
  Leaf,
  LockKeyhole,
  MapPin,
  Paintbrush,
  Scissors,
  Plus,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Target,
  TrendingUp,
  Utensils,
  X,
  Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Section = 'overview' | 'goals' | 'rewards' | 'activity';
type ModalName = 'preferences' | 'workout' | 'verification' | 'reward' | null;
type ActivityStatus = 'Verified' | 'In review' | 'Pending review';

interface Quest {
  category: string;
  title: string;
  current: number;
  target: number;
  unit: string;
  displayCurrent: string;
  displayTarget: string;
  nextStep: string;
  icon: LucideIcon;
  color: string;
}

interface Reward {
  id: string;
  interest: string;
  partner: string;
  title: string;
  detail: string;
  milestone: number;
  icon: LucideIcon;
  color: string;
  code: string;
}

interface ActivityRecord {
  id: number;
  title: string;
  detail: string;
  time: string;
  status: ActivityStatus;
}

const NAV_ITEMS: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: 'overview', label: 'Overview', icon: Home },
  { id: 'goals', label: 'My goals', icon: Target },
  { id: 'rewards', label: 'Rewards', icon: Gift },
  { id: 'activity', label: 'Activity', icon: Activity },
];

const GOAL_OPTIONS = [
  'Weight loss',
  'Weight gain',
  'Boxing',
  'MMA',
  'Running',
  'Walking',
  'Calorie burn',
];

const INTEREST_OPTIONS: { label: string; icon: LucideIcon }[] = [
  { label: 'Reading', icon: BookOpen },
  { label: 'Travel', icon: Compass },
  { label: 'Painting', icon: Paintbrush },
  { label: 'Cooking', icon: Utensils },
  { label: 'Gardening', icon: Leaf },
  { label: 'Tailoring', icon: Scissors },
  { label: 'Shopping', icon: ShoppingBag },
  { label: 'Foodie', icon: Heart },
];

const QUESTS: Quest[] = [
  {
    category: 'Running',
    title: 'Run 100 km this month',
    current: 68.4,
    target: 100,
    unit: 'km',
    displayCurrent: '68.4',
    displayTarget: '100',
    nextStep: '80% · unlock a weekend away',
    icon: Footprints,
    color: 'lime',
  },
  {
    category: 'Boxing',
    title: 'Find your fight rhythm',
    current: 3,
    target: 5,
    unit: 'sessions',
    displayCurrent: '3',
    displayTarget: '5',
    nextStep: '4 of 5 sessions · next checkpoint',
    icon: Dumbbell,
    color: 'coral',
  },
  {
    category: 'Calorie burn',
    title: 'Move for 12,000 active kcal',
    current: 7640,
    target: 12000,
    unit: 'kcal',
    displayCurrent: '7,640',
    displayTarget: '12,000',
    nextStep: '80% · your next reward is close',
    icon: Flame,
    color: 'blue',
  },
  {
    category: 'Walking',
    title: 'Walk 50 km this month',
    current: 31.2,
    target: 50,
    unit: 'km',
    displayCurrent: '31.2',
    displayTarget: '50',
    nextStep: '40 km · keep your streak going',
    icon: Footprints,
    color: 'lime',
  },
  {
    category: 'MMA',
    title: 'Train with focus',
    current: 2,
    target: 4,
    unit: 'sessions',
    displayCurrent: '2',
    displayTarget: '4',
    nextStep: '3 of 4 sessions · next checkpoint',
    icon: Dumbbell,
    color: 'coral',
  },
  {
    category: 'Weight loss',
    title: 'Build a steady 12-week routine',
    current: 8,
    target: 12,
    unit: 'weeks',
    displayCurrent: '8',
    displayTarget: '12',
    nextStep: '9 of 12 weeks · progress over perfection',
    icon: TrendingUp,
    color: 'blue',
  },
  {
    category: 'Weight gain',
    title: 'Make room for strength',
    current: 8,
    target: 12,
    unit: 'sessions',
    displayCurrent: '8',
    displayTarget: '12',
    nextStep: '9 of 12 sessions · build at your pace',
    icon: Dumbbell,
    color: 'coral',
  },
];

const REWARDS: Reward[] = [
  {
    id: 'weekend-away',
    interest: 'Travel',
    partner: 'ROAM & ROOT',
    title: '₹500 off a weekend away',
    detail: 'A change of scene, on us. Take the long way to somewhere lovely.',
    milestone: 80,
    icon: MapPin,
    color: 'travel',
    code: 'GO-SOMEWHERE',
  },
  {
    id: 'supper-club',
    interest: 'Foodie',
    partner: 'COMMON TABLE',
    title: '20% off your next supper',
    detail: 'Good food is even better when you have earned the first bite.',
    milestone: 60,
    icon: Utensils,
    color: 'food',
    code: 'EAT-WELL-20',
  },
  {
    id: 'paper-moon',
    interest: 'Reading',
    partner: 'PAPER MOON BOOKS',
    title: 'A new story, on us',
    detail: 'Pick a paperback for the next quiet hour you make for yourself.',
    milestone: 40,
    icon: BookOpen,
    color: 'books',
    code: 'TURN-ANOTHER',
  },
  {
    id: 'little-atelier',
    interest: 'Painting',
    partner: 'LITTLE ATELIER',
    title: '15% off a paint session',
    detail: 'A little colour for the weekend you have been working toward.',
    milestone: 100,
    icon: Paintbrush,
    color: 'art',
    code: 'MAKE-SOMETHING',
  },
  {
    id: 'sunday-sauce',
    interest: 'Cooking',
    partner: 'SUNDAY SAUCE',
    title: 'A pantry box for your next recipe',
    detail: 'Fresh, thoughtful ingredients for a meal made slowly at home.',
    milestone: 90,
    icon: Utensils,
    color: 'food',
    code: 'COOK-TOGETHER',
  },
  {
    id: 'kindred-garden',
    interest: 'Gardening',
    partner: 'KINDRED GARDEN',
    title: 'A little green for your home',
    detail: 'A starter plant and everything you need to help it thrive.',
    milestone: 100,
    icon: Leaf,
    color: 'garden',
    code: 'GROW-SLOWLY',
  },
  {
    id: 'thread-theory',
    interest: 'Tailoring',
    partner: 'THREAD THEORY',
    title: 'Made-to-measure, for less',
    detail: 'A good fit feels even better when it marks a milestone.',
    milestone: 90,
    icon: ShoppingBag,
    color: 'art',
    code: 'GOOD-FIT-15',
  },
  {
    id: 'slowform',
    interest: 'Shopping',
    partner: 'SLOWFORM',
    title: '₹300 off things that last',
    detail: 'A considered little something for the life you are building.',
    milestone: 80,
    icon: ShoppingBag,
    color: 'books',
    code: 'KEEP-GOING',
  },
];

const WEEK_DATA = [
  { day: 'M', value: 36, label: 'Monday' },
  { day: 'T', value: 52, label: 'Tuesday' },
  { day: 'W', value: 28, label: 'Wednesday' },
  { day: 'T', value: 76, label: 'Thursday' },
  { day: 'F', value: 44, label: 'Friday' },
  { day: 'S', value: 92, label: 'Saturday' },
  { day: 'S', value: 18, label: 'Sunday' },
];

const INITIAL_ACTIVITY: ActivityRecord[] = [
  { id: 1, title: 'Morning run', detail: '4.2 km · Strava', time: 'Today, 8:42 am', status: 'Verified' },
  { id: 2, title: 'Boxing fundamentals', detail: '45 min · FitQuest studio', time: 'Yesterday, 6:18 pm', status: 'Verified' },
  { id: 3, title: 'Active calories', detail: '526 kcal · Apple Health', time: 'Yesterday, 12:05 pm', status: 'In review' },
];

const formatDate = () =>
  new Intl.DateTimeFormat('en-IN', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date());

function progressFor(quest: Quest) {
  return Math.min(100, Math.round((quest.current / quest.target) * 100));
}

export function MVPView() {
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [modal, setModal] = useState<ModalName>(null);
  const [selectedGoals, setSelectedGoals] = useState<string[]>(['Running', 'Boxing', 'Calorie burn']);
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Travel', 'Foodie', 'Reading']);
  const [activityItems, setActivityItems] = useState<ActivityRecord[]>(INITIAL_ACTIVITY);
  const [activityType, setActivityType] = useState('Run');
  const [activityDuration, setActivityDuration] = useState('35');
  const [rewardFilter, setRewardFilter] = useState('All');
  const [activeRewardId, setActiveRewardId] = useState<string | null>(null);
  const [claimedRewards, setClaimedRewards] = useState<string[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [toast, setToast] = useState('');
  const openerRef = useRef<HTMLElement | null>(null);

  const openModal = (name: Exclude<ModalName, null>) => {
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setModal(name);
  };

  const selectedQuests = useMemo(
    () => QUESTS.filter((quest) => selectedGoals.includes(quest.category)),
    [selectedGoals],
  );
  const activeQuest = selectedQuests[0] ?? QUESTS[0];
  const activeProgress = progressFor(activeQuest);
  const matchingRewards = useMemo(
    () => REWARDS.filter((reward) => selectedInterests.includes(reward.interest)),
    [selectedInterests],
  );
  const nextReward = useMemo(() => {
    const relevant = matchingRewards.length ? matchingRewards : REWARDS;
    return relevant.find((reward) => reward.milestone > activeProgress) ?? relevant[0];
  }, [activeProgress, matchingRewards]);
  const rewardFilters = ['All', ...selectedInterests];
  const visibleRewards = useMemo(() => {
    const sorted = [...REWARDS].sort((a, b) => {
      const aMatch = selectedInterests.includes(a.interest) ? 0 : 1;
      const bMatch = selectedInterests.includes(b.interest) ? 0 : 1;
      return aMatch - bMatch;
    });
    if (rewardFilter !== 'All') return sorted.filter((reward) => reward.interest === rewardFilter);
    return sorted;
  }, [rewardFilter, selectedInterests]);
  const activeReward = REWARDS.find((reward) => reward.id === activeRewardId) ?? null;
  const ActiveRewardIcon = activeReward?.icon ?? Gift;

  useEffect(() => {
    if (!toast) return undefined;
    const timeout = window.setTimeout(() => setToast(''), 3200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    if (!modal) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setModal(null);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
      openerRef.current?.focus({ preventScroll: true });
    };
  }, [modal]);

  const openReward = (rewardId: string) => {
    setActiveRewardId(rewardId);
    openModal('reward');
  };

  const toggleValue = (value: string, values: string[], setValues: (next: string[]) => void) => {
    setValues(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  };

  const savePreferences = () => {
    setModal(null);
    setRewardFilter('All');
    setToast('Your goals and interests are saved. Keep going.');
  };

  const submitActivity = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const duration = Number(activityDuration);
    if (!duration || duration < 5) return;
    const timestamp = new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit' }).format(new Date());
    const record: ActivityRecord = {
      id: Date.now(),
      title: `${activityType} session`,
      detail: `${duration} min · added just now`,
      time: `Today, ${timestamp}`,
      status: 'Pending review',
    };
    setActivityItems((items) => [record, ...items]);
    setModal(null);
    setToast('Workout received — it will count once verified.');
  };

  const saveReward = () => {
    if (!activeReward) return;
    if (!claimedRewards.includes(activeReward.id)) {
      setClaimedRewards((items) => [...items, activeReward.id]);
    }
    setModal(null);
    setToast('Voucher saved to your reward shelf.');
  };

  const switchSection = (section: Section) => {
    setActiveSection(section);
    setNotificationsOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="fitquest-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Sidebar
        activeSection={activeSection}
        onNavigate={switchSection}
        onPreferences={() => openModal('preferences')}
        nextReward={nextReward}
        progress={activeProgress}
      />

      <main className="main-content" id="main-content">
        <header className="topbar">
          <div className="welcome-copy">
            <div className="topbar-date"><span className="date-spark" />{formatDate()}</div>
            <h1>Good morning, Mira<span className="period">.</span></h1>
            <p>Your consistency is starting to show.</p>
          </div>
          <div className="topbar-actions">
            <button
              className={`icon-button notification-button${notificationsOpen ? ' is-open' : ''}`}
              type="button"
              aria-label="Notifications"
              aria-haspopup="true"
              aria-expanded={notificationsOpen}
              onClick={() => setNotificationsOpen((isOpen) => !isOpen)}
            >
              <Bell size={18} strokeWidth={1.8} />
              <span className="notification-dot" />
            </button>
            <button className="profile-button" type="button" onClick={() => openModal('preferences')} aria-label="Open your profile and preferences">
              <span className="avatar">MK</span>
              <span className="profile-name">Mira K.</span>
            </button>
            {notificationsOpen && (
              <div className="notification-popover">
                <div className="popover-heading"><span>Just in</span><span className="unread-mark">2 new</span></div>
                <div className="notification-item"><span className="notification-icon"><ShieldCheck size={16} /></span><div><strong>Run verified</strong><small>Your 4.2 km run is in the books.</small></div></div>
                <div className="notification-item"><span className="notification-icon gift-icon"><Gift size={16} /></span><div><strong>A reward is within reach</strong><small>12% more to your next milestone.</small></div></div>
              </div>
            )}
          </div>
        </header>

        {activeSection === 'overview' && (
          <OverviewPage
            activeQuest={activeQuest}
            activeProgress={activeProgress}
            quests={selectedQuests}
            nextReward={nextReward}
            onLogWorkout={() => openModal('workout')}
            onExploreRewards={() => switchSection('rewards')}
            onEditGoals={() => openModal('preferences')}
            onOpenReward={openReward}
            onViewActivity={() => switchSection('activity')}
            onVerificationInfo={() => openModal('verification')}
            selectedInterests={selectedInterests}
          />
        )}

        {activeSection === 'goals' && (
          <GoalsPage
            quests={selectedQuests}
            onEditGoals={() => openModal('preferences')}
            onLogWorkout={() => openModal('workout')}
            onViewActivity={() => switchSection('activity')}
          />
        )}

        {activeSection === 'rewards' && (
          <RewardsPage
            filters={rewardFilters}
            selectedInterests={selectedInterests}
            activeFilter={rewardFilter}
            onFilterChange={setRewardFilter}
            rewards={visibleRewards}
            progress={activeProgress}
            questName={activeQuest.title}
            onOpenReward={openReward}
            onEditInterests={() => openModal('preferences')}
            claimedRewards={claimedRewards}
            onLogWorkout={() => openModal('workout')}
          />
        )}

        {activeSection === 'activity' && (
          <ActivityPage
            activityItems={activityItems}
            onLogWorkout={() => openModal('workout')}
            onVerificationInfo={() => openModal('verification')}
          />
        )}
      </main>

      {modal === 'preferences' && (
        <PreferencesModal
          selectedGoals={selectedGoals}
          selectedInterests={selectedInterests}
          onToggleGoal={(goal) => toggleValue(goal, selectedGoals, setSelectedGoals)}
          onToggleInterest={(interest) => toggleValue(interest, selectedInterests, setSelectedInterests)}
          onClose={() => setModal(null)}
          onSave={savePreferences}
        />
      )}

      {modal === 'workout' && (
        <ModalFrame
          eyebrow="MOVE FIRST, WE'LL HANDLE THE REST"
          title="Log a workout"
          description="Tell us what you did. We’ll check it before it counts toward a milestone."
          onClose={() => setModal(null)}
        >
          <form className="workout-form" onSubmit={submitActivity}>
            <label className="field-label" htmlFor="activity-type">Activity</label>
            <select id="activity-type" value={activityType} onChange={(event) => setActivityType(event.target.value)}>
              <option>Run</option>
              <option>Walk</option>
              <option>Boxing</option>
              <option>MMA</option>
              <option>Strength training</option>
            </select>
            <label className="field-label" htmlFor="activity-duration">How long did you move?</label>
            <div className="duration-field"><input id="activity-duration" type="number" min="5" max="240" value={activityDuration} onChange={(event) => setActivityDuration(event.target.value)} required /><span>minutes</span></div>
            <div className="form-note"><ShieldCheck size={16} /><span>Manual entries stay pending until our verification check is complete.</span></div>
            <button className="button button-dark button-wide" type="submit">Send for verification <ArrowRight size={17} /></button>
          </form>
        </ModalFrame>
      )}

      {modal === 'verification' && (
        <ModalFrame
          eyebrow="FAIR PLAY, ALWAYS"
          title="Every milestone is earned."
          description="Your activity is checked before a reward unlocks — so the wins stay meaningful."
          onClose={() => setModal(null)}
        >
          <div className="verification-steps">
            <div className="verification-step"><span className="step-number">01</span><div><strong>Move your way</strong><p>Connect a tracker or add a workout to your activity log.</p></div><CheckCircle2 size={19} /></div>
            <div className="verification-step"><span className="step-number">02</span><div><strong>We cross-check it</strong><p>Movement data is reviewed against the goal and milestone you chose.</p></div><Clock3 size={19} /></div>
            <div className="verification-step"><span className="step-number">03</span><div><strong>Your reward unlocks</strong><p>Once verified, your voucher is ready to use in your reward shelf.</p></div><Gift size={19} /></div>
          </div>
          <button className="button button-dark button-wide modal-done" type="button" onClick={() => setModal(null)}>Sounds good <Check size={17} /></button>
        </ModalFrame>
      )}

      {modal === 'reward' && activeReward && (
        <ModalFrame
          eyebrow={`${activeReward.interest.toUpperCase()} · ${activeReward.partner}`}
          title={activeReward.title}
          description={activeReward.detail}
          onClose={() => setModal(null)}
        >
          <div className={`reward-detail-art ${activeReward.color}`}>
            <div className="reward-detail-mark"><ActiveRewardIcon size={25} strokeWidth={1.5} /></div>
            <span>THE GOOD THINGS ARE EARNED</span>
            <strong>{activeReward.milestone}%<small> quest milestone</small></strong>
          </div>
          {activeProgress >= activeReward.milestone ? (
            <div className="reward-unlock-note"><CheckCircle2 size={17} /><span>Unlocked on your <strong>{activeQuest.category.toLowerCase()}</strong> quest. Your verification is up to date.</span></div>
          ) : (
            <div className="reward-unlock-note is-locked"><LockKeyhole size={17} /><span><strong>{Math.max(0, activeReward.milestone - activeProgress)}% to go</strong> on your active quest to unlock this reward.</span></div>
          )}
          <div className="reward-modal-actions">
            {activeProgress >= activeReward.milestone ? (
              <button className="button button-dark button-wide" type="button" onClick={saveReward}>
                {claimedRewards.includes(activeReward.id) ? 'Save another voucher' : 'Save my voucher'} <ArrowRight size={17} />
              </button>
            ) : (
              <button className="button button-dark button-wide" type="button" onClick={() => setModal(null)}>Keep moving <ArrowRight size={17} /></button>
            )}
          </div>
        </ModalFrame>
      )}

      {toast && <div className="toast-message" role="status"><CheckCircle2 size={18} /><span>{toast}</span></div>}
    </div>
  );
}

function Sidebar({
  activeSection,
  onNavigate,
  onPreferences,
  nextReward,
  progress,
}: {
  activeSection: Section;
  onNavigate: (section: Section) => void;
  onPreferences: () => void;
  nextReward: Reward | undefined;
  progress: number;
}) {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      <a className="brand-lockup" href="#main-content" aria-label="FitQuest home" onClick={() => onNavigate('overview')}>
        <span className="brand-mark"><span className="brand-mark-inner"><Zap size={19} fill="currentColor" strokeWidth={1.5} /></span></span>
        <span className="brand-wordmark">fit<span>quest</span><small>MOVE INTO MORE</small></span>
      </a>

      <div className="sidebar-section-label">YOUR SPACE</div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            className={`nav-item${activeSection === id ? ' active' : ''}`}
            type="button"
            key={id}
            aria-current={activeSection === id ? 'page' : undefined}
            aria-label={label}
            onClick={() => onNavigate(id)}
          >
            <Icon size={18} strokeWidth={1.8} />
            <span>{label}</span>
            {id === 'rewards' && <span className="nav-count" aria-hidden="true">2</span>}
          </button>
        ))}
      </nav>

      <button className="sidebar-preferences" type="button" onClick={onPreferences}>
        <span className="preferences-icon"><Sparkles size={16} /></span>
        <span><strong>Make it yours</strong><small>Goals & interests</small></span>
        <ChevronRight size={15} className="preferences-arrow" />
      </button>

      <div className="sidebar-reward-card">
        <div className="reward-card-orbit"><Gift size={17} /></div>
        <span className="sidebar-card-label">YOUR NEXT UNLOCK</span>
        <strong>{nextReward?.title ?? 'A little something good'}</strong>
        <div className="sidebar-reward-meta"><span>{nextReward?.milestone ?? 80}% milestone</span><span className="tiny-arrow"><ArrowUpRight size={14} /></span></div>
        <div className="sidebar-mini-track"><span style={{ width: `${nextReward ? Math.min(100, Math.round((progress / nextReward.milestone) * 100)) : progress}%` }} /></div>
      </div>

      <div className="sidebar-bottom">
        <div className="sidebar-divider" />
        <div className="sidebar-user">
          <span className="avatar sidebar-avatar">MK</span>
          <span className="sidebar-user-copy"><strong>Mira Kapoor</strong><small>Quest level 04</small></span>
          <Award size={17} className="user-award" />
        </div>
      </div>
    </aside>
  );
}

function OverviewPage({
  activeQuest,
  activeProgress,
  quests,
  nextReward,
  onLogWorkout,
  onExploreRewards,
  onEditGoals,
  onOpenReward,
  onViewActivity,
  onVerificationInfo,
  selectedInterests,
}: {
  activeQuest: Quest;
  activeProgress: number;
  quests: Quest[];
  nextReward: Reward | undefined;
  onLogWorkout: () => void;
  onExploreRewards: () => void;
  onEditGoals: () => void;
  onOpenReward: (id: string) => void;
  onViewActivity: () => void;
  onVerificationInfo: () => void;
  selectedInterests: string[];
}) {
  const ActiveIcon = activeQuest.icon;
  const NextRewardIcon = nextReward?.icon ?? Gift;
  const remaining = Math.max(0, (nextReward?.milestone ?? 80) - activeProgress);

  return (
    <div className="page-stack">
      <section className="hero-card" aria-label="Your current quest">
        <div className="hero-photo" />
        <div className="hero-grain" />
        <div className="hero-content">
          <div className="hero-eyebrow"><span className="live-indicator" /> THIS MONTH · YOUR QUEST</div>
          <h2>Little by little.<br /><em>Further than ever.</em></h2>
          <p>Every verified milestone brings you closer to a reward that feels like you.</p>
          <div className="hero-actions">
            <button className="button button-lime" type="button" onClick={onLogWorkout}>Log a workout <ArrowUpRight size={17} /></button>
            <button className="hero-text-button" type="button" onClick={onExploreRewards}>Find your reward <ArrowRight size={15} /></button>
          </div>
        </div>
        <div className="hero-side-note"><span>01 — 03</span><span className="hero-side-line" /><span>KEEP GOING</span></div>
        <div className="hero-next-reward">
          <div className="hero-reward-top"><span>NEXT REWARD</span><span className="hero-reward-icon"><NextRewardIcon size={16} /></span></div>
          <strong>{nextReward?.title ?? 'A little something good'}</strong>
          <span className="hero-reward-bottom">{remaining > 0 ? `${remaining}% to your next unlock` : 'Milestone reached · ready to claim'} <ArrowUpRight size={13} /></span>
        </div>
        <div className="hero-progress-block">
          <div className="hero-progress-copy">
            <span><ActiveIcon size={14} /> YOUR FOCUS · {activeQuest.category.toUpperCase()}</span>
            <strong>{activeQuest.displayCurrent}<small> / {activeQuest.displayTarget} {activeQuest.unit}</small></strong>
          </div>
          <div className="hero-progress-track" role="progressbar" aria-label={`${activeQuest.title} progress`} aria-valuenow={activeProgress} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: `${activeProgress}%` }} />
          </div>
          <div className="hero-progress-foot"><span>{activeQuest.title}</span><span>{activeProgress}%</span></div>
        </div>
      </section>

      <section className="stat-row" aria-label="Your weekly progress">
        <StatCard icon={Flame} label="Momentum" value="12 days" note="your longest streak yet" tone="lime" />
        <StatCard icon={Sparkles} label="Quest points" value="840" note="120 earned this week" tone="peach" />
        <StatCard icon={Activity} label="This week" value="4 / 5" note="workouts to your target" tone="blue" />
      </section>

      <div className="dashboard-lower-grid">
        <section className="quest-section">
          <div className="section-heading-row">
            <div>
              <div className="section-kicker">A LITTLE PROGRESS, EVERY DAY</div>
              <h2>Your quests<span className="period">.</span></h2>
            </div>
            <button className="text-link" type="button" onClick={onEditGoals}>Edit goals <ArrowUpRight size={15} /></button>
          </div>
          {quests.length ? (
            <div className="quest-grid">
              {quests.slice(0, 3).map((quest) => <QuestCard key={quest.category} quest={quest} onViewActivity={onViewActivity} />)}
              {quests.length < 4 && (
                <button className="quest-add-card" type="button" onClick={onEditGoals}>
                  <span className="quest-add-icon"><Plus size={17} /></span>
                  <span className="quest-add-copy"><strong>Add another goal</strong><small>Your next chapter can start here.</small></span>
                  <span className="quest-add-arrow" aria-hidden="true"><ArrowUpRight size={15} /></span>
                </button>
              )}
            </div>
          ) : (
            <EmptyState title="Start with one thing." detail="Choose a goal that feels good to work toward." action="Choose goals" onAction={onEditGoals} />
          )}
        </section>

        <aside className="overview-aside">
          {nextReward && (
            <button className="next-reward-panel" type="button" onClick={() => onOpenReward(nextReward.id)}>
              <span className="reward-panel-top"><span>MADE FOR YOUR INTERESTS</span><span className="interest-count">{selectedInterests.length} picked</span></span>
              <span className={`reward-tile-icon ${nextReward.color}`}><NextRewardIcon size={19} strokeWidth={1.65} /></span>
              <span className="reward-panel-title">A little closer to<br /><em>{nextReward.interest.toLowerCase()}.</em></span>
              <span className="reward-panel-copy">{nextReward.title} · unlock at {nextReward.milestone}%</span>
              <span className="reward-panel-track"><i style={{ width: `${Math.min(100, Math.round((activeProgress / nextReward.milestone) * 100))}%` }} /></span>
              <span className="reward-panel-foot"><span>{remaining > 0 ? `${remaining}% until your next reward` : 'Milestone reached'}</span><span className="reward-panel-arrow"><ArrowUpRight size={16} /></span></span>
            </button>
          )}

          <div className="verification-panel">
            <div className="verification-panel-head">
              <span className="verification-shield"><ShieldCheck size={19} /></span>
              <span className="verified-pill"><span /> VERIFIED</span>
            </div>
            <strong>Your wins are the real deal.</strong>
            <p>Activity is cross-checked before a milestone reward unlocks.</p>
            <button className="verification-link" type="button" onClick={onVerificationInfo}>How verification works <ArrowRight size={14} /></button>
          </div>
        </aside>
      </div>

      <div className="bottom-note"><span className="note-mark"><Heart size={14} fill="currentColor" /></span><span>Progress at your pace. Rewards on your terms.</span><button type="button" onClick={onViewActivity}>See recent activity <ArrowRight size={14} /></button></div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, note, tone }: { icon: LucideIcon; label: string; value: string; note: string; tone: string }) {
  return (
    <article className="stat-card">
      <span className={`stat-icon ${tone}`}><Icon size={17} strokeWidth={1.8} /></span>
      <div className="stat-copy"><span className="stat-label">{label}</span><strong>{value}</strong><small>{note}</small></div>
      <span className="stat-corner"><ArrowUpRight size={14} /></span>
    </article>
  );
}

function QuestCard({ quest, onViewActivity }: { quest: Quest; onViewActivity: () => void }) {
  const Icon = quest.icon;
  const progress = progressFor(quest);
  return (
    <article className="quest-card">
      <div className="quest-card-head">
        <span className={`quest-icon ${quest.color}`}><Icon size={17} strokeWidth={1.8} /></span>
        <span className="quest-category">{quest.category}</span>
        <span className="quest-menu-dot" aria-hidden="true">···</span>
      </div>
      <h3>{quest.title}</h3>
      <div className="quest-amount"><strong>{quest.displayCurrent}</strong><span>/ {quest.displayTarget} {quest.unit}</span><em>{progress}%</em></div>
      <div className={`quest-progress ${quest.color}`} role="progressbar" aria-label={`${quest.title} progress`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progress}%` }} /></div>
      <div className="quest-checkpoint"><span className="checkpoint-dot" />{quest.nextStep}</div>
      <button className="quest-card-link" type="button" onClick={onViewActivity}>See activity <ArrowRight size={14} /></button>
    </article>
  );
}

function GoalsPage({ quests, onEditGoals, onLogWorkout, onViewActivity }: { quests: Quest[]; onEditGoals: () => void; onLogWorkout: () => void; onViewActivity: () => void }) {
  return (
    <div className="page-stack inner-page">
      <PageIntro
        eyebrow="THE THINGS YOU'RE WORKING TOWARD"
        title={<>Your goals, <em>your way.</em></>}
        description="Choose the kind of progress that feels good to you. We'll help make it count."
        action={<button className="button button-dark" type="button" onClick={onEditGoals}><Sparkles size={16} /> Customize goals</button>}
      />
      <div className="goals-summary-row">
        <div className="goals-summary-copy"><span className="section-kicker">IN MOTION RIGHT NOW</span><strong>{quests.length.toString().padStart(2, '0')}<small> active quests</small></strong></div>
        <p>Progress is personal. Your quests can change as you do.</p>
        <button className="text-link" type="button" onClick={onLogWorkout}>Log an activity <ArrowUpRight size={15} /></button>
      </div>
      {quests.length ? (
        <div className="goal-page-grid">{quests.map((quest) => <QuestCard key={quest.category} quest={quest} onViewActivity={onViewActivity} />)}</div>
      ) : (
        <EmptyState title="Your next chapter starts here." detail="Pick a goal that fits your life right now. There's no wrong place to begin." action="Choose your goals" onAction={onEditGoals} />
      )}
      <div className="goal-footnote"><ShieldCheck size={17} /><span>Milestones are only marked complete after your activity is verified.</span><button type="button" onClick={onViewActivity}>View activity <ArrowRight size={14} /></button></div>
    </div>
  );
}

function RewardsPage({
  filters,
  selectedInterests,
  activeFilter,
  onFilterChange,
  rewards,
  progress,
  questName,
  onOpenReward,
  onEditInterests,
  claimedRewards,
  onLogWorkout,
}: {
  filters: string[];
  selectedInterests: string[];
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  rewards: Reward[];
  progress: number;
  questName: string;
  onOpenReward: (id: string) => void;
  onEditInterests: () => void;
  claimedRewards: string[];
  onLogWorkout: () => void;
}) {
  return (
    <div className="page-stack inner-page">
      <PageIntro
        eyebrow="GOOD THINGS, WELL EARNED"
        title={<>A reward for <em>being you.</em></>}
        description="The things you love can be the reason you keep showing up."
        action={<button className="button button-dark" type="button" onClick={onEditInterests}><Heart size={16} /> Tune my interests</button>}
      />
      <div className="reward-shelf-banner">
        <div className="shelf-banner-icon"><Gift size={21} /></div>
        <div><span className="section-kicker">YOUR INTERESTS, YOUR REWARDS</span><strong>{selectedInterests.length ? `${selectedInterests.length} interests in your orbit` : 'A whole shelf of possibilities'}</strong></div>
        <span className="shelf-banner-progress"><span className="shelf-progress-number">{progress}%</span><span>on your<br />active quest</span></span>
        <div className="shelf-banner-quest"><span>YOUR ACTIVE QUEST</span><strong>{questName}</strong></div>
      </div>
      <div className="reward-filter-header">
        <div><div className="section-kicker">PICKED FOR WHAT YOU LOVE</div><h2>Your reward shelf<span className="period">.</span></h2></div>
        <span className="sample-rewards-label"><span /> PARTNER PREVIEWS</span>
      </div>
      <p className="filter-caption">{selectedInterests.length ? <>Curated around <strong>{selectedInterests.join(' · ')}</strong>. Add an interest to bring its rewards into the spotlight.</> : <>Every partner reward in one place. Add interests to curate your shelf.</>}</p>
      <div className="filter-list" role="group" aria-label="Filter rewards by interest">
        {filters.map((filter) => (
          <button type="button" key={filter} className={`filter-chip${activeFilter === filter ? ' selected' : ''}`} aria-pressed={activeFilter === filter} onClick={() => onFilterChange(filter)}>
            {filter === 'All' && <Sparkles size={14} />}{filter}
          </button>
        ))}
        {!selectedInterests.length && <button className="filter-chip" type="button" onClick={onEditInterests}><Plus size={14} /> Choose interests</button>}
      </div>
      {rewards.length ? (
        <div className={`reward-layout${activeFilter === 'All' ? ' is-full' : ''}`}>
          <div className="reward-grid">
            {rewards.map((reward) => <RewardCard key={reward.id} reward={reward} progress={progress} onOpen={onOpenReward} claimed={claimedRewards.includes(reward.id)} inInterests={selectedInterests.length === 0 || selectedInterests.includes(reward.interest)} />)}
          </div>
          {activeFilter !== 'All' && (
            <aside className="interest-spotlight" aria-label={`${activeFilter} interest spotlight`}>
              <span className="spotlight-index">0{Math.max(1, filters.indexOf(activeFilter))} / 0{filters.length - 1}</span>
              <span className="section-kicker">INTEREST SPOTLIGHT</span>
              <h3>For the love of <em>{activeFilter.toLowerCase()}.</em></h3>
              <p>Rewards from this corner of your life appear as milestones are verified. Keep moving and the shelf keeps filling.</p>
              <div className="spotlight-milestone"><span>NEXT MILESTONE</span><strong>{Math.min(100, Math.ceil((progress + 1) / 10) * 10)}%</strong></div>
              <div className="spotlight-track"><span style={{ width: `${progress}%` }} /></div>
              <div className="spotlight-foot"><span>{progress}% on your active quest</span><button type="button" onClick={onLogWorkout}>Log activity <ArrowUpRight size={14} /></button></div>
            </aside>
          )}
        </div>
      ) : (
        <EmptyState title="No rewards in this corner yet." detail="Choose another interest or add a new one to your profile." action="Update interests" onAction={onEditInterests} />
      )}
      <p className="rewards-disclaimer">Rewards shown are examples for this FitQuest concept. Partner offers and milestone values can be configured by FitQuest.</p>
    </div>
  );
}

function RewardCard({ reward, progress, onOpen, claimed, inInterests }: { reward: Reward; progress: number; onOpen: (id: string) => void; claimed: boolean; inInterests: boolean }) {
  const Icon = reward.icon;
  const unlocked = progress >= reward.milestone;
  return (
    <article className={`reward-card ${reward.color}${unlocked ? ' unlocked' : ' locked'}${inInterests ? '' : ' is-outside'}`}>
      <div className="reward-card-art">
        <span className="reward-card-tag">{reward.interest.toUpperCase()}</span>
        <span className="reward-card-icon"><Icon size={22} strokeWidth={1.6} /></span>
        <span className="reward-card-edition">FITQUEST / PERK {String(reward.milestone).padStart(2, '0')}</span>
        {!unlocked && <span className="reward-lock-mark"><LockKeyhole size={13} /></span>}
      </div>
      <div className="reward-card-body">
        <div className="reward-partner">{reward.partner}</div>
        <h3>{reward.title}</h3>
        <p>{reward.detail}</p>
        <div className="reward-card-footer">
          <span className={unlocked ? 'reward-status-open' : 'reward-status-locked'}>{!inInterests ? <><Sparkles size={12} /> ADD {reward.interest.toUpperCase()}</> : unlocked ? <><CheckCircle2 size={14} /> {claimed ? 'SAVED TO YOUR SHELF' : 'MILESTONE UNLOCKED'}</> : <><LockKeyhole size={13} /> UNLOCK AT {reward.milestone}%</>}</span>
          <button className="reward-card-button" type="button" onClick={() => onOpen(reward.id)} aria-label={`${unlocked ? 'View' : 'See how to unlock'} ${reward.title}`}><ArrowUpRight size={17} /></button>
        </div>
        {!unlocked && <div className="reward-mini-progress"><span style={{ width: `${Math.min(100, Math.round((progress / reward.milestone) * 100))}%` }} /></div>}
      </div>
    </article>
  );
}

function ActivityPage({ activityItems, onLogWorkout, onVerificationInfo }: { activityItems: ActivityRecord[]; onLogWorkout: () => void; onVerificationInfo: () => void }) {
  const pendingCount = activityItems.filter((item) => item.status !== 'Verified').length;
  return (
    <div className="page-stack inner-page">
      <PageIntro
        eyebrow="PROOF OF THE GOOD WORK"
        title={<>Look how far <em>you've come.</em></>}
        description="Every walk, round, and little bit of effort adds up."
        action={<button className="button button-dark" type="button" onClick={onLogWorkout}><Plus size={17} /> Log activity</button>}
      />
      <div className="activity-top-grid">
        <section className="activity-chart-card">
          <div className="activity-chart-heading"><div><span className="section-kicker">YOUR MOVEMENT, LATELY</span><h2>A week in motion<span className="period">.</span></h2></div><span className="chart-period">THIS WEEK <ChevronRight size={14} /></span></div>
          <div className="weekly-chart" role="img" aria-label="Activity chart showing movement across all seven days this week">
            {WEEK_DATA.map((item, index) => (
              <div className={`chart-column${index === 5 ? ' chart-highlight' : ''}`} key={`${item.label}-${index}`}>
                <div className="chart-bar-area"><span className="chart-bar" style={{ height: `${item.value}%` }} /></div>
                <span className="chart-day">{item.day}</span>
              </div>
            ))}
          </div>
          <div className="chart-caption"><span><i className="chart-legend-dot" /> Active minutes</span><strong>246 <small>mins this week</small></strong></div>
        </section>
        <section className="verification-summary-card">
          <div className="verification-summary-top"><span className="verification-large-icon"><ShieldCheck size={23} /></span><span className="verified-pill"><span /> TRUSTED</span></div>
          <span className="section-kicker">MILESTONE CHECK</span>
          <h2>Wins worth<br /><em>celebrating.</em></h2>
          <p>FitQuest checks activity before it turns into a reward. Your progress stays yours.</p>
          <div className="verification-summary-bottom"><span>{pendingCount} activity {pendingCount === 1 ? 'entry' : 'entries'} to review</span><button type="button" onClick={onVerificationInfo} aria-label="How verification works"><ArrowUpRight size={17} /></button></div>
        </section>
      </div>

      <section className="activity-log-section">
        <div className="section-heading-row activity-log-heading"><div><div className="section-kicker">THE SMALL WINS ADD UP</div><h2>Recent activity<span className="period">.</span></h2></div><span className="log-source"><span className="source-dot" /> TRACKER SYNC ON</span></div>
        <div className="activity-list">
          {activityItems.map((item) => <ActivityRow key={item.id} item={item} />)}
        </div>
      </section>
      <div className="goal-footnote activity-footnote"><ShieldCheck size={17} /><span>Verified activity unlocks the milestones you earn.</span><button type="button" onClick={onVerificationInfo}>How it works <ArrowRight size={14} /></button></div>
    </div>
  );
}

function ActivityRow({ item }: { item: ActivityRecord }) {
  const verified = item.status === 'Verified';
  return (
    <article className="activity-row">
      <span className={`activity-row-icon${verified ? ' verified' : ''}`}>{verified ? <Check size={17} /> : item.status === 'In review' ? <Clock3 size={17} /> : <Activity size={17} />}</span>
      <div className="activity-row-main"><strong>{item.title}</strong><span>{item.detail}</span></div>
      <span className="activity-row-time">{item.time}</span>
      <span className={`activity-status${verified ? ' is-verified' : item.status === 'In review' ? ' is-review' : ' is-pending'}`}><i />{item.status}</span>
      <ChevronRight className="activity-row-chevron" size={16} />
    </article>
  );
}

function PageIntro({ eyebrow, title, description, action }: { eyebrow: string; title: ReactNode; description: string; action?: ReactNode }) {
  return (
    <div className="page-intro">
      <div className="page-intro-copy"><span className="section-kicker">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>
      {action && <div className="page-intro-action">{action}</div>}
    </div>
  );
}

function EmptyState({ title, detail, action, onAction }: { title: string; detail: string; action: string; onAction: () => void }) {
  return (
    <div className="empty-state"><span className="empty-state-icon"><Sparkles size={22} /></span><h3>{title}</h3><p>{detail}</p><button className="button button-dark" type="button" onClick={onAction}>{action} <ArrowRight size={16} /></button></div>
  );
}

function PreferencesModal({
  selectedGoals,
  selectedInterests,
  onToggleGoal,
  onToggleInterest,
  onClose,
  onSave,
}: {
  selectedGoals: string[];
  selectedInterests: string[];
  onToggleGoal: (goal: string) => void;
  onToggleInterest: (interest: string) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <ModalFrame
      eyebrow="BUILT AROUND YOUR LIFE"
      title="Make this yours."
      description="Pick the goals that matter now and the interests that make progress feel like a present."
      onClose={onClose}
      wide
    >
      <div className="preference-group">
        <div className="preference-group-title"><span>01</span><div><strong>Your goals</strong><small>Choose what you want to work toward.</small></div></div>
        <div className="preference-chips">
          {GOAL_OPTIONS.map((goal) => {
            const selected = selectedGoals.includes(goal);
            return <button key={goal} className={`preference-chip${selected ? ' selected' : ''}`} type="button" aria-pressed={selected} onClick={() => onToggleGoal(goal)}>{selected && <Check size={14} />}{goal}</button>;
          })}
        </div>
      </div>
      <div className="preference-group">
        <div className="preference-group-title"><span>02</span><div><strong>Your interests</strong><small>We'll find rewards that feel like you.</small></div></div>
        <div className="preference-chips interest-preference-chips">
          {INTEREST_OPTIONS.map(({ label, icon: Icon }) => {
            const selected = selectedInterests.includes(label);
            return <button key={label} className={`preference-chip interest-chip${selected ? ' selected' : ''}`} type="button" aria-pressed={selected} onClick={() => onToggleInterest(label)}><Icon size={15} />{label}{selected && <Check size={13} className="interest-chip-check" />}</button>;
          })}
        </div>
      </div>
      <div className="preference-footer"><span><ShieldCheck size={16} /> Change your goals or interests whenever life changes.</span><button className="button button-dark" type="button" onClick={onSave}>Save my setup <ArrowRight size={16} /></button></div>
    </ModalFrame>
  );
}

function ModalFrame({
  eyebrow,
  title,
  description,
  onClose,
  children,
  wide = false,
}: {
  eyebrow: string;
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className={`modal-card${wide ? ' modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close dialog" autoFocus><X size={19} /></button>
        <div className="modal-heading"><span className="section-kicker">{eyebrow}</span><h2>{title}</h2><p>{description}</p></div>
        {children}
      </section>
    </div>
  );
}
