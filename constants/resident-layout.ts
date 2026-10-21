import { StyleSheet } from 'react-native';

/** Shared geometry for resident screens, based on the Home tab cover layout. */
export const residentLayout = StyleSheet.create({
  header: {
    backgroundColor: '#07419C',
    borderTopLeftRadius: 0,
    borderTopRightRadius: 0,
    marginHorizontal: 0,
    marginTop: 0,
    minHeight: 190,
    overflow: 'hidden',
    paddingBottom: 44,
    paddingHorizontal: 24,
    paddingTop: 32,
  },
  overlapCard: {
    borderColor: '#C9D9F8',
    borderRadius: 18,
    borderWidth: 1,
    marginHorizontal: 18,
    marginTop: -24,
  },
  card: {
    borderRadius: 16,
    marginHorizontal: 18,
    marginTop: 10,
  },
});
