import { api } from './api.js';
import { formatDuration, formatPace, shortDate } from './format.js';

const { createApp } = Vue;

createApp({
  data() {
    return {
      activeTab: 'log',
      tabs: [
        { id: 'log', label: 'Тренування' },
        { id: 'plan', label: 'План підготовки' },
        { id: 'gear', label: 'Кросівки' },
        { id: 'zones', label: 'Зони та обсяги' },
      ],
      typeLabels: {
        easy: 'Легкий',
        long: 'Довгий',
        tempo: 'Темповий',
        intervals: 'Інтервали',
        race: 'Забіг',
      },
      phaseLabels: {
        build: 'Розвиток обсягу',
        recovery: 'Розвантажувальний тиждень',
        taper: 'Підведення до старту',
      },
      statusLabels: {
        ok: 'у нормі',
        warning: 'слідкуйте',
        critical: 'скоро заміна',
        replace: 'замінити',
        retired: 'списані',
        unknown: 'невідомо',
      },
      trendLabels: {
        growth: 'зростає',
        stable: 'стабільна',
        sharp_increase: 'різкий стрибок',
        sharp_drop: 'різкий спад',
        restart: 'рестарт',
        not_enough_data: 'мало даних',
      },
      loading: true,
      error: '',
      runner: null,
      runs: [],
      shoes: [],
      gear: {},
      zones: [],
      weekly: [],
      insights: {},
      plan: [],
      newRun: { distance_km: 8, duration_min: 42, avg_hr: null, workout_type: 'easy', shoe_id: null },
      newShoe: { model: '', category: 'daily', mileage_km: 0 },
      planRequest: { target_distance_km: 10, weeks: 8 },
    };
  },

  computed: {
    levelLabel() {
      const labels = { beginner: 'Початківець', intermediate: 'Середній рівень', advanced: 'Просунутий' };
      return labels[this.runner.level] || this.runner.level;
    },
    trendLabel() {
      return this.trendLabels[this.insights.trend] || '—';
    },
    maxWeeklyVolume() {
      return this.weekly.reduce((max, week) => Math.max(max, week.total_km), 1);
    },
  },

  methods: {
    formatDuration,
    shortDate,

    formatPace(run) {
      return `${formatPace(run.distance_km, run.duration_sec)} /км`;
    },

    barHeight(totalKm) {
      return `${Math.max((totalKm / this.maxWeeklyVolume) * 100, 4)}%`;
    },

    async loadAll() {
      this.loading = true;
      this.error = '';
      try {
        const runners = await api.listRunners();
        if (runners.length === 0) {
          this.runner = null;
          return;
        }
        this.runner = runners[0];
        await this.refresh();
      } catch (err) {
        this.error = `Не вдалося завантажити дані: ${err.message}`;
      } finally {
        this.loading = false;
      }
    },

    async refresh() {
      const id = this.runner.id;
      const [runs, shoes, gear, zones, weekly, insights] = await Promise.all([
        api.listRuns(id),
        api.listShoes(id),
        api.gearOverview(id),
        api.zones(id),
        api.weekly(id),
        api.insights(id),
      ]);
      this.runs = runs;
      this.shoes = shoes;
      this.gear = gear;
      this.zones = zones;
      this.weekly = weekly;
      this.insights = insights;
    },

    async addRun() {
      try {
        await api.createRun({
          runner_id: this.runner.id,
          shoe_id: this.newRun.shoe_id,
          distance_km: this.newRun.distance_km,
          duration_sec: Math.round(this.newRun.duration_min * 60),
          avg_hr: this.newRun.avg_hr || null,
          workout_type: this.newRun.workout_type,
        });
        await this.refresh();
      } catch (err) {
        this.error = `Тренування не збережено: ${err.message}`;
      }
    },

    async addShoe() {
      try {
        await api.createShoe({
          runner_id: this.runner.id,
          model: this.newShoe.model,
          category: this.newShoe.category,
          mileage_km: this.newShoe.mileage_km,
        });
        this.newShoe.model = '';
        await this.refresh();
      } catch (err) {
        this.error = `Пару не додано: ${err.message}`;
      }
    },

    async buildPlan() {
      try {
        const result = await api.createPlan({
          runner_id: this.runner.id,
          target_distance_km: this.planRequest.target_distance_km,
          weeks: this.planRequest.weeks,
        });
        this.plan = result.plan;
      } catch (err) {
        this.error = `План не згенеровано: ${err.message}`;
      }
    },
  },

  mounted() {
    this.loadAll();
  },
}).mount('#app');
