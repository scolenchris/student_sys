<template>
  <el-card class="trend-card">
    <template #header>
      <div class="header-row">
        <span>班级全年级排名趋势</span>
      </div>
    </template>

    <el-form :inline="true" class="filter-bar">
      <el-form-item label="趋势维度">
        <el-select
          v-model="query.context_key"
          placeholder="请选择学年/届别/科目"
          style="width: 280px"
          @change="handleContextChange"
        >
          <el-option
            v-for="ctx in contexts"
            :key="ctx.context_key"
            :label="formatContextLabel(ctx)"
            :value="ctx.context_key"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="班级">
        <el-select
          v-model="query.class_id"
          clearable
          placeholder="默认全部我的班级"
          style="width: 220px"
          :disabled="!selectedContext"
          @change="fetchTrend"
        >
          <el-option
            v-for="cls in classOptions"
            :key="cls.class_id"
            :label="cls.class_name"
            :value="cls.class_id"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="loading" @click="fetchTrend">
          生成趋势图
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="说明"
      description="排名口径为单科班均分级排名，名次越小越靠前（1名最好）。"
      style="margin-bottom: 10px"
    />

    <el-alert
      v-if="warnings.length"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 10px"
    >
      <template #title>注意</template>
      <template #default>
        <div v-for="(w, idx) in warnings" :key="idx">{{ w }}</div>
      </template>
    </el-alert>

    <div v-loading="loading" class="chart-wrap">
      <div ref="chartRef" class="chart-box"></div>
    </div>

    <div v-if="detailRows.length > 0" class="detail-wrap">
      <div class="detail-title">趋势核对明细（考试 x 班级）</div>
      <el-table :data="detailRows" border stripe style="width: 100%">
        <el-table-column prop="exam_label" label="考试" width="180" fixed />
        <el-table-column
          v-for="item in trendSeries"
          :key="item.class_id"
          :label="item.class_name"
          align="center"
        >
          <el-table-column
            :prop="`rank_${item.class_id}`"
            label="级排"
            width="80"
            align="center"
          />
          <el-table-column
            :prop="`avg_${item.class_id}`"
            label="班均分"
            width="90"
            align="center"
          />
          <el-table-column
            :prop="`people_${item.class_id}`"
            label="人数"
            width="80"
            align="center"
          />
        </el-table-column>
      </el-table>
    </div>
  </el-card>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import * as echarts from "echarts";
import { getClassRankTrend, getRankTrendContexts } from "../../api/teacher";

const loading = ref(false);
const contexts = ref([]);
const exams = ref([]);
const trendSeries = ref([]);
const warnings = ref([]);

const query = reactive({
  context_key: "",
  class_id: null,
});

const chartRef = ref(null);
let chartInstance = null;

const selectedContext = computed(() =>
  contexts.value.find((ctx) => ctx.context_key === query.context_key),
);

const classOptions = computed(() => selectedContext.value?.classes || []);
const detailRows = computed(() => {
  if (exams.value.length === 0 || trendSeries.value.length === 0) return [];

  return exams.value.map((exam, examIdx) => {
    const row = {
      exam_label: exam.x_label,
    };

    trendSeries.value.forEach((item) => {
      row[`rank_${item.class_id}`] = item.ranks?.[examIdx] ?? "-";
      row[`avg_${item.class_id}`] = item.avg_scores?.[examIdx] ?? "-";
      row[`people_${item.class_id}`] = item.exam_people?.[examIdx] ?? 0;
    });

    return row;
  });
});

const formatContextLabel = (ctx) => {
  return `${ctx.academic_year}学年 / ${ctx.entry_year}级 / ${ctx.subject_name}`;
};

const getTrendParams = () => {
  if (!selectedContext.value) return null;
  const params = {
    entry_year: selectedContext.value.entry_year,
    academic_year: selectedContext.value.academic_year,
    subject_id: selectedContext.value.subject_id,
  };
  if (query.class_id) {
    params.class_id = query.class_id;
  }
  return params;
};

const ensureChart = () => {
  if (!chartRef.value) return null;
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }
  return chartInstance;
};

const renderChart = () => {
  const chart = ensureChart();
  if (!chart) return;

  const xLabels = exams.value.map((item) => item.x_label);
  const hasSeries = trendSeries.value.length > 0;
  const hasExam = xLabels.length > 0;

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "line" },
      formatter: (params) => {
        if (!params || params.length === 0) return "";
        const dataIndex = params[0].dataIndex;
        const exam = exams.value[dataIndex];
        const lines = [`<strong>${exam?.x_label || "-"}</strong>`];

        params.forEach((p) => {
          const item = trendSeries.value[p.seriesIndex];
          if (!item) return;
          const rank = item.ranks?.[dataIndex];
          const avg = item.avg_scores?.[dataIndex];
          const people = item.exam_people?.[dataIndex];
          lines.push(
            `${p.marker}${item.class_name}：级排 ${rank ?? "-"}，班均分 ${avg ?? "-"}，考试人数 ${people ?? 0}`,
          );
        });

        return lines.join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      top: 10,
      data: trendSeries.value.map((item) => item.class_name),
    },
    grid: {
      left: 45,
      right: 20,
      top: 62,
      bottom: 30,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: xLabels,
      axisLabel: {
        interval: 0,
        rotate: 20,
      },
    },
    yAxis: {
      type: "value",
      inverse: true,
      minInterval: 1,
      name: "级排名",
      nameTextStyle: { padding: [0, 0, 0, 10] },
    },
    series: trendSeries.value.map((item) => ({
      name: item.class_name,
      type: "line",
      smooth: false,
      connectNulls: false,
      symbolSize: 8,
      data: item.ranks.map((rank) => (rank === null || rank === undefined ? null : rank)),
    })),
    graphic:
      hasSeries && hasExam
        ? []
        : [
            {
              type: "text",
              left: "center",
              top: "middle",
              style: {
                text: "暂无可展示的趋势数据",
                fill: "#909399",
                fontSize: 14,
              },
            },
          ],
  };

  chart.setOption(option, true);
};

const fetchContexts = async () => {
  try {
    const res = await getRankTrendContexts();
    contexts.value = Array.isArray(res.data) ? res.data : [];

    if (contexts.value.length === 0) {
      exams.value = [];
      trendSeries.value = [];
      warnings.value = ["当前账号暂无可查看的趋势上下文。"];
      await nextTick();
      renderChart();
      return;
    }

    query.context_key = contexts.value[0].context_key;
    query.class_id = null;
    await fetchTrend();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "获取趋势维度失败");
  }
};

const fetchTrend = async () => {
  const params = getTrendParams();
  if (!params) return;

  loading.value = true;
  try {
    const res = await getClassRankTrend(params);
    const data = res.data || {};
    exams.value = Array.isArray(data.exams) ? data.exams : [];
    trendSeries.value = Array.isArray(data.series) ? data.series : [];
    warnings.value = Array.isArray(data.warnings) ? data.warnings : [];

    await nextTick();
    renderChart();
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || "获取排名趋势失败");
    exams.value = [];
    trendSeries.value = [];
    warnings.value = [];
    await nextTick();
    renderChart();
  } finally {
    loading.value = false;
  }
};

const handleContextChange = async () => {
  query.class_id = null;
  await fetchTrend();
};

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize();
  }
};

onMounted(async () => {
  await fetchContexts();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<style scoped>
.trend-card {
  min-height: 82vh;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.filter-bar {
  margin-bottom: 10px;
  padding: 14px 14px 0 14px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.chart-wrap {
  width: 100%;
  min-height: 500px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.chart-box {
  width: 100%;
  height: 520px;
}

.detail-wrap {
  margin-top: 14px;
}

.detail-title {
  margin-bottom: 8px;
  font-weight: 600;
  color: #303133;
}
</style>
