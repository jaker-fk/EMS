<template>
  <div>
    <section class="page-head">
      <div class="site-container">
        <h1>关于启明学堂</h1>
        <p>一所专注「把课讲清楚」的社区型教培机构</p>
      </div>
    </section>

    <section class="site-section">
      <div class="site-container intro">
        <div class="intro-text">
          <h2>我们是谁</h2>
          <p>
            启明学堂成立于 2016 年，目前在海淀区设有 2 个教学点，开设少儿编程、学科辅导、
            语言培训与艺术素养四大课程体系，累计服务 1200+ 组家庭。
          </p>
          <p>
            我们不做大规模的广告投放，学员绝大多数来自老家长推荐。课程定价、师资背景、
            退费规则全部公开在官网，报名前可以随时到校区旁听。
          </p>
          <p>
            我们相信：教培的价值不在于「多上了几节课」，而在于孩子是否真的弄懂了一个问题、
            是否愿意继续学下去。
          </p>
        </div>

        <div class="intro-stats">
          <div v-for="item in stats" :key="item.label" class="stat">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="site-section site-section--muted">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">HOW IT WORKS</div>
          <h2 class="section-title">从咨询到上课，只需要四步</h2>
        </div>

        <div class="steps">
          <div v-for="(step, index) in steps" :key="step.title" class="step">
            <span class="step-no">{{ index + 1 }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="site-section">
      <div class="site-container contact">
        <div class="campus">
          <h2>校区信息</h2>
          <ul>
            <li><strong>中关村校区</strong>北京市海淀区知春路 66 号 3 层</li>
            <li><strong>五道口校区</strong>北京市海淀区成府路 28 号院 2 号楼 201</li>
            <li><strong>咨询电话</strong><a href="tel:4008601234">400-860-1234</a></li>
            <li><strong>工作时间</strong>09:00 - 20:30（周一至周日）</li>
            <li><strong>轨道交通</strong>地铁 10 号线知春路站 B 口步行 300 米</li>
          </ul>
        </div>

        <div class="faq">
          <h2>常见问题</h2>
          <el-collapse v-model="activeFaq">
            <el-collapse-item v-for="(item, index) in faqs" :key="item.q" :name="String(index)">
              <template #title>{{ item.q }}</template>
              <p class="faq-a">{{ item.a }}</p>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </section>

    <section class="cta">
      <div class="site-container cta-inner">
        <div>
          <h2>想先看看课堂是什么样？</h2>
          <p>预约一节免费的试听课，和主讲老师聊十分钟再做决定。</p>
        </div>
        <RouterLink to="/courses" class="cta-btn">进入课程中心</RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../../utils/request'
import type { SiteHomeData } from '../../utils/site'

const activeFaq = ref('0')
const stats = ref([
  { label: '创办年份', value: '2016' },
  { label: '在校学员', value: '600+' },
  { label: '开设课程', value: '—' },
  { label: '授课教师', value: '—' },
])

const steps = [
  { title: '免费咨询', desc: '电话或官网留资，课程顾问了解孩子年级、目标与可上课时间。' },
  { title: '入学测评', desc: '到校做一次 40 分钟的摸底测评，明确当前水平与薄弱点。' },
  { title: '定制课表', desc: '按测评结果推荐班型，支持先试听 1 节再决定是否报名。' },
  { title: '每月反馈', desc: '主讲老师每月出具学情报告，并可与家长线上一对一沟通。' },
]

const faqs = [
  {
    q: '可以先试听再报名吗？',
    a: '可以。所有班课都支持免费试听 1 节，试听后再决定是否报名，不产生任何费用。',
  },
  {
    q: '报名后不满意能退费吗？',
    a: '前 3 次课内不满意可申请全额退费（扣除已发放教材成本），3 次课后按剩余课时比例退费，不设违约金。',
  },
  {
    q: '一个班多少人？',
    a: '班课为 6 人小班，配备主讲与助教各 1 名；一对一课程按学员时间单独排课。',
  },
  {
    q: '缺课了怎么办？',
    a: '提前 1 天请假可安排到同进度平行班补课，或在下一期同课程免费重修该讲。',
  },
  {
    q: '有线上课吗？',
    a: '编程与语言类课程支持线上双师授课，学科辅导建议线下面授，具体可咨询课程顾问。',
  },
]

onMounted(async () => {
  try {
    const data = (await api.get('/site/home')) as unknown as SiteHomeData
    stats.value = [
      { label: '创办年份', value: '2016' },
      { label: '累计报名', value: `${data.stats.enrollments}+` },
      { label: '开设课程', value: `${data.stats.courses}` },
      { label: '授课教师', value: `${data.stats.teachers}` },
    ]
  } catch {
    /* 统计失败时保留占位数据 */
  }
})
</script>

<style scoped>
.page-head {
  padding: 52px 0 40px;
  background: radial-gradient(circle at 20% 10%, #e2eeff 0%, #f7faff 60%, #fff 100%);
}

.page-head h1 {
  margin: 0 0 10px;
  font-size: 32px;
  color: #0f1c2e;
}

.page-head p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.intro {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 48px;
  align-items: center;
}

.intro-text h2,
.campus h2,
.faq h2 {
  margin: 0 0 18px;
  font-size: 22px;
  color: #0f1c2e;
}

.intro-text p {
  margin: 0 0 14px;
  color: #4b5563;
  font-size: 14.5px;
  line-height: 2;
}

.intro-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stat {
  padding: 22px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f2f7ff, #ffffff);
  border: 1px solid #e6eefc;
  text-align: center;
}

.stat strong {
  display: block;
  font-size: 24px;
  color: #1677ff;
}

.stat span {
  font-size: 12px;
  color: #8a919f;
}

.steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.step {
  background: #fff;
  border: 1px solid #eaeef6;
  border-radius: 14px;
  padding: 26px 22px;
  position: relative;
}

.step-no {
  display: inline-flex;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  color: #fff;
  font-weight: 600;
  margin-bottom: 14px;
}

.step h3 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #0f1c2e;
}

.step p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.8;
}

.contact {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 48px;
}

.campus ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.campus li {
  color: #4b5563;
  font-size: 14px;
  line-height: 1.8;
}

.campus li strong {
  display: inline-block;
  min-width: 84px;
  color: #0f1c2e;
}

.campus a {
  color: #1677ff;
  text-decoration: none;
}

.faq-a {
  margin: 0;
  color: #5c6675;
  font-size: 14px;
  line-height: 1.9;
}

.cta {
  background: linear-gradient(135deg, #0f3d8f, #1677ff);
  color: #fff;
  padding: 48px 0;
}

.cta-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.cta h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.cta p {
  margin: 0;
  color: #cfe0ff;
  font-size: 14px;
}

.cta-btn {
  display: inline-block;
  padding: 13px 30px;
  border-radius: 999px;
  background: #fff;
  color: #1677ff;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 900px) {
  .intro,
  .contact {
    grid-template-columns: 1fr;
    gap: 28px;
  }
}
</style>
