import { StyleSheet } from 'react-native';

/** Shared semantic type scale. Individual screens keep their colors and layout. */
export const appTypography = StyleSheet.create({
  pageTitle: { fontSize: 24, fontWeight: '800', lineHeight: 32 },
  pageSubtitle: { fontSize: 13, fontWeight: '400', lineHeight: 19 },
  majorSection: { fontSize: 20, fontWeight: '700', lineHeight: 27 },
  sectionTitle: { fontSize: 17, fontWeight: '700', lineHeight: 23 },
  cardTitle: { fontSize: 17, fontWeight: '600', lineHeight: 23 },
  fieldLabel: { fontSize: 14, fontWeight: '600', lineHeight: 20 },
  body: { fontSize: 14, fontWeight: '400', lineHeight: 20 },
  input: { fontSize: 15, fontWeight: '400', lineHeight: 21 },
  helper: { fontSize: 12, fontWeight: '400', lineHeight: 17 },
  button: { fontSize: 15, fontWeight: '700', lineHeight: 21 },
  tabLabel: { fontSize: 10, fontWeight: '600', lineHeight: 14 },
});
