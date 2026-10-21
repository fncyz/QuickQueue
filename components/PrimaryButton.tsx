import {
  TouchableOpacity,
  StyleSheet,
  TouchableOpacityProps,
} from "react-native";
import { Text } from '@/components/Typography';
import { appTypography } from '@/constants/typography';

interface Props extends TouchableOpacityProps {
  title: string;
}

export default function PrimaryButton({
  title,
  ...props
}: Props) {
  return (
    <TouchableOpacity
      style={styles.button}
      activeOpacity={0.8}
      {...props}
    >
      <Text style={styles.text}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: "#1E88E5",
    padding: 15,
    borderRadius: 10,
    alignItems: "center",
  },
  text: {
    ...appTypography.button,
    color: "#fff",
  },
});
