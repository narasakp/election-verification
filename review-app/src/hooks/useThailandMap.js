import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { geoPath, geoMercator, geoCentroid } from 'd3-geo'
import { feature } from 'topojson-client'

// English→Thai province name mapping (TopoJSON NAME_1 → Thai name used in data)
// Two variants for Bangkok & Ayutthaya — callers can override via aliasMap
export const EN_TO_TH = {
  'Amnat Charoen': 'อำนาจเจริญ',
  'Ang Thong': 'อ่างทอง',
  'Bangkok Metropolis': 'กรุงเทพมหานคร',
  'Buri Ram': 'บุรีรัมย์',
  'Chachoengsao': 'ฉะเชิงเทรา',
  'Chai Nat': 'ชัยนาท',
  'Chaiyaphum': 'ชัยภูมิ',
  'Chanthaburi': 'จันทบุรี',
  'Chiang Mai': 'เชียงใหม่',
  'Chiang Rai': 'เชียงราย',
  'Chon Buri': 'ชลบุรี',
  'Chumphon': 'ชุมพร',
  'Kalasin': 'กาฬสินธุ์',
  'Kamphaeng Phet': 'กำแพงเพชร',
  'Kanchanaburi': 'กาญจนบุรี',
  'Khon Kaen': 'ขอนแก่น',
  'Krabi': 'กระบี่',
  'Lampang': 'ลำปาง',
  'Lamphun': 'ลำพูน',
  'Loei': 'เลย',
  'Lop Buri': 'ลพบุรี',
  'Mae Hong Son': 'แม่ฮ่องสอน',
  'Maha Sarakham': 'มหาสารคาม',
  'Mukdahan': 'มุกดาหาร',
  'Nakhon Nayok': 'นครนายก',
  'Nakhon Pathom': 'นครปฐม',
  'Nakhon Phanom': 'นครพนม',
  'Nakhon Ratchasima': 'นครราชสีมา',
  'Nakhon Sawan': 'นครสวรรค์',
  'Nakhon Si Thammarat': 'นครศรีธรรมราช',
  'Nan': 'น่าน',
  'Narathiwat': 'นราธิวาส',
  'Nong Bua Lam Phu': 'หนองบัวลำภู',
  'Nong Khai': 'หนองคาย',
  'Nonthaburi': 'นนทบุรี',
  'Pathum Thani': 'ปทุมธานี',
  'Pattani': 'ปัตตานี',
  'Phangnga': 'พังงา',
  'Phatthalung': 'พัทลุง',
  'Phayao': 'พะเยา',
  'Phetchabun': 'เพชรบูรณ์',
  'Phetchaburi': 'เพชรบุรี',
  'Phichit': 'พิจิตร',
  'Phitsanulok': 'พิษณุโลก',
  'Phra Nakhon Si Ayutthaya': 'พระนครศรีอยุธยา',
  'Phrae': 'แพร่',
  'Phuket': 'ภูเก็ต',
  'Prachin Buri': 'ปราจีนบุรี',
  'Prachuap Khiri Khan': 'ประจวบคีรีขันธ์',
  'Ranong': 'ระนอง',
  'Ratchaburi': 'ราชบุรี',
  'Rayong': 'ระยอง',
  'Roi Et': 'ร้อยเอ็ด',
  'Sa Kaeo': 'สระแก้ว',
  'Sakon Nakhon': 'สกลนคร',
  'Samut Prakan': 'สมุทรปราการ',
  'Samut Sakhon': 'สมุทรสาคร',
  'Samut Songkhram': 'สมุทรสงคราม',
  'Saraburi': 'สระบุรี',
  'Satun': 'สตูล',
  'Si Sa Ket': 'ศรีสะเกษ',
  'Sing Buri': 'สิงห์บุรี',
  'Songkhla': 'สงขลา',
  'Sukhothai': 'สุโขทัย',
  'Suphan Buri': 'สุพรรณบุรี',
  'Surat Thani': 'สุราษฎร์ธานี',
  'Surin': 'สุรินทร์',
  'Tak': 'ตาก',
  'Trang': 'ตรัง',
  'Trat': 'ตราด',
  'Ubon Ratchathani': 'อุบลราชธานี',
  'Udon Thani': 'อุดรธานี',
  'Uthai Thani': 'อุทัยธานี',
  'Uttaradit': 'อุตรดิตถ์',
  'Yala': 'ยะลา',
  'Yasothon': 'ยโสธร',
  'Bueng Kan': 'บึงกาฬ',
}

// Short names for display on map (long Thai names get truncated)
export const SHORT_NAMES = {
  'กรุงเทพมหานคร': 'กทม.',
  'กรุงเทพ': 'กทม.',
  'นครราชสีมา': 'โคราช',
  'นครศรีธรรมราช': 'นครศรีฯ',
  'ประจวบคีรีขันธ์': 'ประจวบฯ',
  'สมุทรปราการ': 'สมุทรปราการ',
  'สมุทรสาคร': 'สมุทรสาคร',
  'สมุทรสงคราม': 'สมุทรสงคราม',
  'อุบลราชธานี': 'อุบลฯ',
  'กาญจนบุรี': 'กาญจนบุรี',
  'สุราษฎร์ธานี': 'สุราษฎร์ฯ',
  'หนองบัวลำภู': 'หนองบัวฯ',
  'พระนครศรีอยุธยา': 'อยุธยา',
  'อำนาจเจริญ': 'อำนาจฯ',
  'กำแพงเพชร': 'กำแพงเพชร',
  'ฉะเชิงเทรา': 'ฉะเชิงเทรา',
  'แม่ฮ่องสอน': 'แม่ฮ่องสอน',
  'เพชรบูรณ์': 'เพชรบูรณ์',
}

// Skip lake features
export const SKIP_FEATURES = new Set([
  'Phatthalung (Songkhla Lake)',
  'Songkhla (Songkhla Lake)',
])

export const MAP_WIDTH = 1600
export const MAP_HEIGHT = 2000

/**
 * Custom hook for loading & projecting Thailand TopoJSON map.
 *
 * @param {object} options
 * @param {boolean} options.enabled  — whether to load the TopoJSON (e.g. when panel is expanded)
 * @param {object}  [options.aliasMap] — optional EN→TH overrides merged on top of default EN_TO_TH
 * @returns {{ geoFeatures, pathGen, projection, loadError, resolveThaiName, svgRef, hoveredProv, setHoveredProv, mousePos, handleMouseMove }}
 */
export default function useThailandMap({ enabled = true, aliasMap } = {}) {
  const [geoFeatures, setGeoFeatures] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [hoveredProv, setHoveredProv] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const svgRef = useRef(null)

  // Merged alias map
  const nameMap = useMemo(() => {
    if (!aliasMap) return EN_TO_TH
    return { ...EN_TO_TH, ...aliasMap }
  }, [aliasMap])

  // Load TopoJSON
  useEffect(() => {
    if (!enabled) return
    if (geoFeatures) return

    fetch(`${import.meta.env.BASE_URL}thailand-provinces.topojson`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(topo => {
        const objectKey = Object.keys(topo.objects)[0]
        const fc = feature(topo, topo.objects[objectKey])
        // Filter out lake features
        fc.features = fc.features.filter(f => !SKIP_FEATURES.has(f.properties.NAME_1))
        setGeoFeatures(fc)
      })
      .catch(err => setLoadError(err.message))
  }, [enabled, geoFeatures])

  // D3 projection + path generator
  const { pathGen, projection } = useMemo(() => {
    if (!geoFeatures) return { pathGen: null, projection: null }
    const proj = geoMercator().fitSize([MAP_WIDTH, MAP_HEIGHT], geoFeatures)
    return { pathGen: geoPath().projection(proj), projection: proj }
  }, [geoFeatures])

  // Mouse move handler for tooltip positioning (relative to SVG)
  const handleMouseMove = useCallback((e) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [])

  // Resolve English TopoJSON name → Thai name
  const resolveThaiName = useCallback((enName) => {
    return nameMap[enName] || enName
  }, [nameMap])

  return {
    geoFeatures,
    pathGen,
    projection,
    loadError,
    resolveThaiName,
    svgRef,
    hoveredProv,
    setHoveredProv,
    mousePos,
    handleMouseMove,
  }
}
