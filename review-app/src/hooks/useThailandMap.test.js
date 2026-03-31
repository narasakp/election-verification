import { describe, it, expect } from 'vitest'
import { EN_TO_TH, SHORT_NAMES, SKIP_FEATURES, MAP_WIDTH, MAP_HEIGHT } from './useThailandMap'

describe('EN_TO_TH province mapping', () => {
  it('contains 77 provinces (76 + Bueng Kan)', () => {
    // Thailand has 77 provinces including Bueng Kan
    expect(Object.keys(EN_TO_TH).length).toBe(77)
  })

  it('maps Bangkok correctly', () => {
    expect(EN_TO_TH['Bangkok Metropolis']).toBe('กรุงเทพมหานคร')
  })

  it('maps Chiang Mai correctly', () => {
    expect(EN_TO_TH['Chiang Mai']).toBe('เชียงใหม่')
  })

  it('maps Phuket correctly', () => {
    expect(EN_TO_TH['Phuket']).toBe('ภูเก็ต')
  })

  it('maps Bueng Kan (newest province)', () => {
    expect(EN_TO_TH['Bueng Kan']).toBe('บึงกาฬ')
  })

  it('maps Phra Nakhon Si Ayutthaya correctly', () => {
    expect(EN_TO_TH['Phra Nakhon Si Ayutthaya']).toBe('พระนครศรีอยุธยา')
  })

  it('all values are non-empty Thai strings', () => {
    Object.entries(EN_TO_TH).forEach(([en, th]) => {
      expect(th).toBeTruthy()
      expect(typeof th).toBe('string')
      // Thai characters are in Unicode range 0E00-0E7F
      expect(/[\u0E00-\u0E7F]/.test(th)).toBe(true)
    })
  })

  it('has no duplicate Thai names', () => {
    const thNames = Object.values(EN_TO_TH)
    const unique = new Set(thNames)
    expect(unique.size).toBe(thNames.length)
  })
})

describe('SHORT_NAMES', () => {
  it('provides short name for กรุงเทพมหานคร', () => {
    expect(SHORT_NAMES['กรุงเทพมหานคร']).toBe('กทม.')
  })

  it('provides short name for กรุงเทพ (alias)', () => {
    expect(SHORT_NAMES['กรุงเทพ']).toBe('กทม.')
  })

  it('provides short name for นครราชสีมา', () => {
    expect(SHORT_NAMES['นครราชสีมา']).toBe('โคราช')
  })

  it('returns undefined for provinces without short names', () => {
    expect(SHORT_NAMES['เชียงใหม่']).toBeUndefined()
  })
})

describe('SKIP_FEATURES', () => {
  it('is a Set', () => {
    expect(SKIP_FEATURES).toBeInstanceOf(Set)
  })

  it('contains lake features to skip', () => {
    expect(SKIP_FEATURES.has('Phatthalung (Songkhla Lake)')).toBe(true)
    expect(SKIP_FEATURES.has('Songkhla (Songkhla Lake)')).toBe(true)
  })

  it('has exactly 2 entries', () => {
    expect(SKIP_FEATURES.size).toBe(2)
  })

  it('does not contain normal province names', () => {
    expect(SKIP_FEATURES.has('Chiang Mai')).toBe(false)
    expect(SKIP_FEATURES.has('Bangkok Metropolis')).toBe(false)
  })
})

describe('MAP dimensions', () => {
  it('MAP_WIDTH is 1600', () => {
    expect(MAP_WIDTH).toBe(1600)
  })

  it('MAP_HEIGHT is 2000', () => {
    expect(MAP_HEIGHT).toBe(2000)
  })
})
