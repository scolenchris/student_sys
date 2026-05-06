import { computed, ref } from "vue";

export const LAYOUT_SIZE_STORAGE_KEY = "app_layout_size";

export const layoutSizeOptions = [
  { value: "default", label: "默认" },
  { value: "large", label: "放大" },
  { value: "xlarge", label: "超大" },
];

const DEFAULT_LAYOUT_SIZE = "default";
const optionValues = new Set(layoutSizeOptions.map((item) => item.value));
const currentLayoutSize = ref(DEFAULT_LAYOUT_SIZE);
let initialized = false;

function normalizeLayoutSize(value) {
  return optionValues.has(value) ? value : DEFAULT_LAYOUT_SIZE;
}

function applyLayoutSize(value) {
  if (typeof document === "undefined") return;
  document.documentElement.dataset.layoutSize = normalizeLayoutSize(value);
}

export function initLayoutSize() {
  if (initialized) return;
  initialized = true;

  const storedValue =
    typeof localStorage === "undefined"
      ? DEFAULT_LAYOUT_SIZE
      : localStorage.getItem(LAYOUT_SIZE_STORAGE_KEY);

  currentLayoutSize.value = normalizeLayoutSize(storedValue);
  applyLayoutSize(currentLayoutSize.value);
}

export function setLayoutSize(value) {
  const nextValue = normalizeLayoutSize(value);
  currentLayoutSize.value = nextValue;
  applyLayoutSize(nextValue);

  if (typeof localStorage !== "undefined") {
    localStorage.setItem(LAYOUT_SIZE_STORAGE_KEY, nextValue);
  }
}

export function clearAuthStorageKeepLayoutSize() {
  if (typeof localStorage === "undefined") return;

  const storedLayoutSize =
    localStorage.getItem(LAYOUT_SIZE_STORAGE_KEY) || currentLayoutSize.value;

  localStorage.clear();
  localStorage.setItem(
    LAYOUT_SIZE_STORAGE_KEY,
    normalizeLayoutSize(storedLayoutSize),
  );
}

export function useLayoutSize() {
  initLayoutSize();

  const currentLabel = computed(() => {
    return (
      layoutSizeOptions.find((item) => item.value === currentLayoutSize.value)
        ?.label || "默认"
    );
  });

  return {
    currentLabel,
    layoutSize: currentLayoutSize,
    layoutSizeOptions,
    setLayoutSize,
  };
}
