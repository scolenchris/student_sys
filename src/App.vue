<template>
  <router-view />
</template>

<script setup>
import { initLayoutSize } from "./composables/useLayoutSize";

initLayoutSize();
</script>
