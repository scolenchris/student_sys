<template>
  <div class="layout-size-switcher" aria-label="显示大小调整">
    <span class="switcher-label">显示大小</span>
    <el-radio-group
      v-model="selectedSize"
      class="size-options"
      size="small"
      aria-label="显示大小"
    >
      <el-radio-button
        v-for="option in layoutSizeOptions"
        :key="option.value"
        :label="option.value"
      >
        {{ option.label }}
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useLayoutSize } from "../composables/useLayoutSize";

const { layoutSize, layoutSizeOptions, setLayoutSize } = useLayoutSize();

const selectedSize = computed({
  get: () => layoutSize.value,
  set: (value) => setLayoutSize(value),
});
</script>

<style scoped>
.layout-size-switcher {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border: 1px solid #dce8f5;
  border-radius: 12px;
  background: rgba(247, 251, 255, 0.92);
  color: #3f5f7f;
  white-space: nowrap;
}

.switcher-label {
  font-size: var(--app-font-size-small);
  font-weight: 600;
}

.size-options :deep(.el-radio-button__inner) {
  padding: 6px 10px;
  font-size: var(--app-font-size-small);
  font-weight: 600;
}

@media (max-width: 760px) {
  .layout-size-switcher {
    align-self: flex-start;
  }
}
</style>
