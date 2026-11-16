import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 全局注册 Element Plus 图标：菜单表里只存图标名，前端按名字动态渲染
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component as never)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
