import re

path = 'src/components/features/QualityView.tsx'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<button className="btn btn-glass"', '<MagneticButton className="btn-glass"')
text = text.replace('<button className="btn btn-primary"', '<MagneticButton className="btn-primary"')
text = text.replace('</button>', '</MagneticButton>')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

path2 = 'src/pages/DashboardPage.tsx'
with open(path2, 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = text2.replace('<button ', '<MagneticButton ')
text2 = text2.replace('<button\n', '<MagneticButton\n')
text2 = text2.replace('</button>', '</MagneticButton>')

with open(path2, 'w', encoding='utf-8') as f:
    f.write(text2)

with open('src/pages/DashboardPage.tsx', 'r', encoding='utf-8') as f:
    dashboard = f.read()

if 'import { MagneticButton }' not in dashboard:
    dashboard = dashboard.replace('import { motion, AnimatePresence } from \'framer-motion\';', 
    '''import { motion, AnimatePresence } from 'framer-motion';
import { MagneticButton } from '../components/MagneticButton';''')
    with open('src/pages/DashboardPage.tsx', 'w', encoding='utf-8') as f:
        f.write(dashboard)

print('Success')
