<script setup lang="ts">

import { computed } from "vue";
import type { Attitude } from "../composables/useWebSocket";

const props = defineProps<{
  attitude: Attitude | null;
}>();

const rollDeg = computed(() => props.attitude ? (props.attitude.roll * 180) / Math.PI : 0);
const pitchDeg = computed(() => props.attitude ? (props.attitude.pitch * 180) / Math.PI : 0);
const yawDeg = computed(() => {
  if (!props.attitude) return 0;
  const deg = (props.attitude.yaw * 180) / Math.PI;
  return (deg + 360) % 360;
});

const PX_PER_DEG = 8;
const ladderShift = computed(() => pitchDeg.value * PX_PER_DEG);
const pitchMarks = [45, 30, 15, 0, -15, -30, -45];

const headingMarks = computed(() => {
  const marks: { deg: number; label: string }[] = [];
  for (let d = -90; d <= 90; d += 15) {
    const abs = (Math.round((yawDeg.value + d) / 15) * 15 + 360) % 360;
    marks.push({ deg: d, label: cardinal(abs) });
  }
  return marks;
});

function cardinal(deg: number): string {
  const map: Record<number, string> = {
    0: "N", 90: "E", 180: "S", 270: "W",
    45: "NE", 135: "SE", 225: "SW", 315: "NW",
  };
  return map[deg] ?? String(deg);
}
</script>


<template>

  <div class="hud">

    <!-- bracket central -->
    <div class="bracket" :style="{ transform: `rotate(${rollDeg}deg)` }">
      <div class="arc arc-left" />
      <div class="arc arc-right" />
      <div class="tick tick-left" />
      <div class="tick tick-right" />
    </div>

    <!-- pitch ladder lateral esquerda -->
    <div class="ladder ladder-left">
      <div
        class="ladder-inner"
        :style="{ transform: `translateY(${ladderShift}px) rotate(${rollDeg}deg)` }"
      >
        <div
          v-for="m in pitchMarks"
          :key="`l${m}`"
          class="rung"
          :class="{ 'rung-zero': m === 0 }"
          :style="{ top: `${-m * PX_PER_DEG}px` }"
        >
          <span class="rung-num">{{ m }}</span>
          <span class="rung-line" />
        </div>
      </div>
    </div>

    <!-- pitch ladder lateral direita -->
    <div class="ladder ladder-right">
      <div
        class="ladder-inner"
        :style="{ transform: `translateY(${ladderShift}px) rotate(${rollDeg}deg)` }"
      >
        <div
          v-for="m in pitchMarks"
          :key="`r${m}`"
          class="rung rung-r"
          :class="{ 'rung-zero': m === 0 }"
          :style="{ top: `${-m * PX_PER_DEG}px` }"
        >
          <span class="rung-line" />
          <span class="rung-num">{{ m }}</span>
        </div>
      </div>
    </div>

    <!-- fita de heading -->
    <div class="heading">
      <div class="heading-value">{{ yawDeg.toFixed(1) }}°</div>
      <div class="heading-caret" />
      <div class="heading-tape">
        <span
          v-for="m in headingMarks"
          :key="m.deg"
          class="heading-mark"
          :style="{ left: `calc(50% + ${m.deg * 3}px)` }"
        >
          {{ m.label }}
        </span>
      </div>
    </div>
  </div>

</template>


<style scoped>
.hud {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  font-family: ui-monospace, "SF Mono", "Roboto Mono", monospace;
  color: rgba(255, 255, 255, 0.92);
  text-shadow: 0 0 3px rgba(0, 0, 0, 0.6);
}

.bracket {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 240px;
  height: 200px;
  translate: -50% -50%;
}

.arc {
  position: absolute;
  top: 50%;
  width: 70px;
  height: 150px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  translate: 0 -50%;
}
.arc-left {
  left: 10px;
  border-right: none;
  border-top: none;
  border-bottom: none;
  border-radius: 100px 0 0 100px;
}
.arc-right {
  right: 10px;
  border-left: none;
  border-top: none;
  border-bottom: none;
  border-radius: 0 100px 100px 0;
}

.tick {
  position: absolute;
  top: 50%;
  width: 40px;
  height: 2px;
  background: rgba(255, 255, 255, 0.9);
  translate: 0 -50%;
}
.tick-left { left: -30px; }
.tick-right { right: -30px; }

.ladder {
  position: absolute;
  top: 50%;
  width: 90px;
  height: 0;
}
.ladder-left { left: 22%; }
.ladder-right { right: 22%; }

.ladder-inner {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
}

.rung {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}
.rung-r { justify-content: flex-end; }

.rung-line {
  display: block;
  width: 36px;
  height: 1.5px;
  background: rgba(255, 255, 255, 0.85);
}
.rung:not(.rung-zero) .rung-line {
  background: repeating-linear-gradient(
    to right,
    rgba(255, 255, 255, 0.85) 0 6px,
    transparent 6px 11px
  );
}
.rung-zero .rung-line {
  width: 44px;
  height: 2px;
}

.rung-num {
  font-size: 11px;
  font-weight: 500;
  min-width: 18px;
  text-align: center;
  opacity: 0.85;
}

.heading {
  position: absolute;
  bottom: 6%;
  left: 50%;
  translate: -50%;
  width: 420px;
  height: 44px;
}
.heading-value {
  position: absolute;
  top: -4px;
  left: 50%;
  translate: -50%;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.heading-caret {
  position: absolute;
  top: 18px;
  left: 50%;
  translate: -50%;
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 7px solid rgba(255, 255, 255, 0.95);
}
.heading-tape {
  position: absolute;
  top: 28px;
  left: 0;
  width: 100%;
  height: 16px;
  border-top: 1.5px solid rgba(255, 255, 255, 0.5);
}
.heading-mark {
  position: absolute;
  top: 2px;
  translate: -50%;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.85;
}
</style>
